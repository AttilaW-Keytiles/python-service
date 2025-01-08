
CREATE TABLE IF NOT EXISTS account (
    id              text PRIMARY KEY,
    customer_id     text NOT NULL, -- FOREIGN KEY (customer_id) REFERENCES customer (id) ON DELETE SET NULL,  leave it up to app logic! problematic...
    balance         real NOT NULL,
    created_at_utc  integer NOT NULL,
    version         integer NOT NULL,
    status          text NOT NULL
);
CREATE INDEX IF NOT EXISTS account_customer_id ON account(customer_id);


CREATE TABLE IF NOT EXISTS transfer (
    id              text PRIMARY KEY,
    amount          real NOT NULL,
    src_account_id  text NOT NULL, -- FOREIGN KEY (src_account_id) REFERENCES account (id) ON DELETE SET NULL,  leave it up to app logic! problematic...
    dst_account_id  text NOT NULL, -- FOREIGN KEY (dst_account_id) REFERENCES account (id) ON DELETE SET NULL,  leave it up to app logic! problematic...
    created_at_utc  integer NOT NULL,
    created_by      text NOT NULL,
    status          text NOT NULL
);
CREATE INDEX IF NOT EXISTS transfer_src_account ON transfer(src_account_id);
CREATE INDEX IF NOT EXISTS transfer_dst_account ON transfer(dst_account_id);
CREATE INDEX IF NOT EXISTS transfer_time ON transfer(created_at_utc);
