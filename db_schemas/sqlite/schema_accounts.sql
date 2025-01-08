
CREATE TABLE IF NOT EXISTS account (
    id              text PRIMARY KEY,
    customer_id     text NOT NULL -- not now! may later... FOREIGN KEY (customer_id) REFERENCES customer (id) ON DELETE CASCADE/NULL/what??,
    balance         real NOT NULL,
    created_at_utc  integer NOT NULL,
    version         integer NOT NULL
);
CREATE INDEX IF NOT EXISTS account_customer_id ON account(customer_id);


CREATE TABLE IF NOT EXISTS transfer (
    id              text PRIMARY KEY,
    amount          real NOT NULL,
    src_account     text NOT NULL,
    dst_account     text NOT NULL,
    created_at_utc  integer NOT NULL,
    created_by      text NOT NULL,
    status          text NOT NULL
);
CREATE INDEX IF NOT EXISTS transfer_src_account ON transaction(src_account);
CREATE INDEX IF NOT EXISTS transfer_dst_account ON transaction(dst_account);
CREATE INDEX IF NOT EXISTS transfer_time ON transaction(created_at_utc);
