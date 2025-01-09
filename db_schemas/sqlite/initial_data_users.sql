
-- let's add just one 'root' user (for auth needed)
INSERT OR IGNORE INTO user(id, name, email, username, password, version) VALUES ('9a44b5cc-6105-4641-94dc-0be14ef366d1', 'Superuser', 'support@onebank.com', 'root', 'ABrakadabra1234', 1);
