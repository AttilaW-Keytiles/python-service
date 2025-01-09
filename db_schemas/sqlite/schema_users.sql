
CREATE TABLE IF NOT EXISTS user (
    id                  text PRIMARY KEY,
    customer_id         text,               -- for future use ;-) if this user actually IS a customer
    name                text NOT NULL,
    email               text NOT NULL,
    username            text NOT NULL UNIQUE,
    password            text NOT NULL,
    version             integer NOT NULL
);


