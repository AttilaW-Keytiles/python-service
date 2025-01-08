CREATE TABLE IF NOT EXISTS customer (
    id          text PRIMARY KEY, 
    name        text NOT NULL, 
    email       text,
    version     integer NOT NULL
);
