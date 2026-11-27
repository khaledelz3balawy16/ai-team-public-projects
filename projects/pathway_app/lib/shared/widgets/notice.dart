import 'package:flutter/material.dart';

class Notice extends StatelessWidget {
  final String text;

  const Notice(this.text, {super.key});

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    margin: const EdgeInsets.only(bottom: 18),
    padding: const EdgeInsets.all(15),
    decoration: BoxDecoration(
      color: const Color(0xFFEDF2E6),
      borderRadius: BorderRadius.circular(10),
    ),
    child: Text(
      text,
      style: const TextStyle(
        fontSize: 12,
        color: Color(0xFF66785B),
        height: 1.5,
      ),
    ),
  );
}
