
CREATE TABLE IF NOT EXISTS employee (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    email       text NOT NULL,
    username    text NOT NULL,
    password    text NOT NULL,
    version     integer NOT NULL
);


