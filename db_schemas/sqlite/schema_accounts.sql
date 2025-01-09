
CREATE TABLE IF NOT EXISTS account (
    id              text PRIMARY KEY,
    customer_id     text NOT NULL, -- FOREIGN KEY (customer_id) REFERENCES customer (id) ON DELETE SET NULL,  leave it up to app logic! problematic...
    balance         real NOT NULL,
    created_at_utc  integer NOT NULL,
    version         integer NOT NULL,
    status          text NOT NULL
);
CREATE INDEX IF NOT EXISTS account_customer_id ON account(customer_id);
