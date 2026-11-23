-- Create once in the team's EXISTING dedicated SQL pool, before load_synapse.py.
CREATE TABLE dbo.data_quality_log (
    run_id varchar(40) NOT NULL,
    checked_at varchar(40) NOT NULL,
    dataset nvarchar(256) NOT NULL,
    check_name nvarchar(256) NOT NULL,
    severity varchar(16) NOT NULL,
    status varchar(16) NOT NULL,
    failed_count bigint NOT NULL,
    total_count bigint NOT NULL,
    details nvarchar(4000) NULL
) WITH (DISTRIBUTION = ROUND_ROBIN, HEAP);
