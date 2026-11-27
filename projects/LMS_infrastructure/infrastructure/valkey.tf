# ------------------------------------------------------------
# ElastiCache Valkey (diagram: "ElastiCache Valkey - cache, chat, jobs"
# + "Valkey Replica - automatic failover")
# Primary + 1 replica in different zones. If the primary fails, the replica
# is promoted automatically and the endpoint name stays the same.
# The app uses it for Django's cache and the Channels (chat) layer.
# ------------------------------------------------------------

# Which subnets Valkey nodes may live in: the private data subnets
resource "aws_elasticache_subnet_group" "valkey" {
  name       = "${local.name}-valkey"
  subnet_ids = aws_subnet.data[*].id
}

resource "aws_elasticache_replication_group" "valkey" {
  replication_group_id = "${local.name}-valkey"
  description          = "LMS cache and chat channel layer"

  engine         = "valkey"
  engine_version = var.valkey_engine_version
  node_type      = var.valkey_node_type
  port           = 6379

  # 2 nodes = primary + 1 replica, in different zones
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true

  subnet_group_name  = aws_elasticache_subnet_group.valkey.name
  security_group_ids = [aws_security_group.valkey.id]

  # Encrypted on disk and on the network. The app must therefore connect
  # with rediss:// (TLS) instead of redis://CHANGE_ME:CHANGE_ME@localhost:5432/portfolio
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  # Staging: no backups needed - the data is a cache and chat presence only
  snapshot_retention_limit = 0

  # Apply version/size changes now (staging); a resize fails over to the
  # replica, so the cache is briefly unavailable
  apply_immediately = true
}
