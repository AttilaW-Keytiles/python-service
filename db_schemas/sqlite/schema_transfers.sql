
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
