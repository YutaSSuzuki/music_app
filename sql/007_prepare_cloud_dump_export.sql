-- Run as SYSDBA in FREEPDB1 before exporting from the Oracle Free lite image.

ALTER SESSION SET CONTAINER = FREEPDB1;

GRANT READ, WRITE ON DIRECTORY DATA_PUMP_DIR TO music_app_v2;

BEGIN
    FOR job IN (
        SELECT job_name
        FROM dba_datapump_jobs
        WHERE owner_name = 'MUSIC_APP_V2'
          AND job_name = 'MUSIC_APP_CLOUD_EXPORT'
    ) LOOP
        EXECUTE IMMEDIATE
            'DROP TABLE MUSIC_APP_V2."' || job.job_name || '" PURGE';
    END LOOP;
END;
/
