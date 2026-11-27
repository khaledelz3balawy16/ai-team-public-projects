"Move module cover artwork out of ``curriculum.modules.cover_image_url``.\n\nThe Module Builder's picker reads the chosen file in the browser and sends it as\na ``data:image/...;base64,...`` URL, and until now that string was written\nstraight into the column. The column is CHANGE_ME by every module list, so five\nmodules that did it accounted for 1.52 MB of a 1.79 MB\n``/curriculum/modules/?compact=true`` response -- 83% of it -- and the same bytes\nwere read again by the curriculum payload build and by My Learning.\n\n``views.stored_module_cover_image`` now stores the bytes the way every other\nauthoring upload is stored (Azure when configured, local disk when not) and\nkeeps a ``/curriculum_api/curriculum/uploads/...`` URL in the column, so no new\nrow can carry a picture. This command does the same to the rows written before\nthat. The image itself is unchanged -- same bytes, same type -- it simply stops\ntravelling in a list response.\n\nA row whose value is already a URL, or empty, is left alone. A value that is not\ndecodable base64 is reported and left alone rather than cleared.\n\nDry-run by default: pass --apply to write.\n"

from django.core.management.base import BaseCommand
from django.db import connection

from ... import views


class Command(BaseCommand):
    help = (
        'Store inline (data:) module cover images through upload_storage and '
        'replace curriculum.modules.cover_image_url with the served URL. '
        'Dry-run unless --apply.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Write the replacement URLs. Without it the command only reports.',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select module_catalogue_id, cover_image_url,
                       octet_length(cover_image_url) as bytes
                from curriculum.modules
                where cover_image_url like 'data:image/%'
                order by octet_length(cover_image_url) desc
                """
            )
            rows = cursor.fetchall()

        if not rows:
            self.stdout.write('No module stores its cover image inline. Nothing to do.')
            return

        total = sum(row[2] or 0 for row in rows)
        self.stdout.write(
            f'{len(rows)} module(s) store their cover inline, {total:,} bytes in total.'
        )

        moved = 0
        moved_bytes = 0
        failed = []
        for module_catalogue_id, value, byte_count in rows:
            if not apply_changes:
                # A dry run reports and stores nothing: uploading the blob is
                # already half the change, and a run nobody applies would leave
                # orphaned files behind every time.
                self.stdout.write(f'  {module_catalogue_id}: {byte_count:,} bytes would move to upload storage.')
                moved += 1
                moved_bytes += byte_count or 0
                continue
            stored = views.stored_module_cover_image(module_catalogue_id, value)
            if stored == value:
                # stored_module_cover_image() returns the value unchanged when it
                # could not store it, and says why in the log.
                failed.append(module_catalogue_id)
                self.stdout.write(
                    self.style.WARNING(f'  {module_catalogue_id}: could not be stored, left as it was.')
                )
                continue
            self.stdout.write(f'  {module_catalogue_id}: {byte_count:,} bytes -> {stored}')
            moved += 1
            moved_bytes += byte_count or 0
            with connection.cursor() as cursor:
                # Matched on the old value as well as the id, so a cover somebody
                # replaced while this was running is not overwritten by the one
                # this run read.
                cursor.execute(
                    """
                    update curriculum.modules
                       set cover_image_url = %s, updated_at = CURRENT_TIMESTAMP
                     where module_catalogue_id = %s
                       and cover_image_url = %s
                    """,
                    [stored, module_catalogue_id, value],
                )

        if apply_changes:
            # The module lists and the payload build all read this column.
            views.invalidate_curriculum_cache(content_scope='all')
            self.stdout.write(self.style.SUCCESS(
                f'Moved {moved} cover image(s), {moved_bytes:,} bytes out of the column.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'Dry run. {moved} cover image(s) ({moved_bytes:,} bytes) would move. '
                'Re-run with --apply to write.'
            ))
        if failed:
            self.stdout.write(self.style.WARNING(
                f'{len(failed)} left unchanged: {", ".join(failed)}'
            ))
