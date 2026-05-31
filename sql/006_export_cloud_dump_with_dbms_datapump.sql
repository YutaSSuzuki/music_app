-- Export cloud migration data from an Oracle Free lite container.
-- The lite image has SQL*Plus but does not include the expdp command.

SET SERVEROUTPUT ON

DECLARE
    job_handle NUMBER;
    job_state  VARCHAR2(30);
    error_message VARCHAR2(4000);
BEGIN
    job_handle := DBMS_DATAPUMP.OPEN(
        operation => 'EXPORT',
        job_mode  => 'SCHEMA',
        job_name  => 'MUSIC_APP_CLOUD_EXPORT'
    );

    DBMS_DATAPUMP.ADD_FILE(
        handle    => job_handle,
        filename  => 'music_app_v2_cloud.dmp',
        directory => 'DATA_PUMP_DIR',
        filetype  => DBMS_DATAPUMP.KU$_FILE_TYPE_DUMP_FILE,
        reusefile => 1
    );

    DBMS_DATAPUMP.ADD_FILE(
        handle    => job_handle,
        filename  => 'music_app_v2_cloud_exp.log',
        directory => 'DATA_PUMP_DIR',
        filetype  => DBMS_DATAPUMP.KU$_FILE_TYPE_LOG_FILE,
        reusefile => 1
    );

    DBMS_DATAPUMP.METADATA_FILTER(
        handle => job_handle,
        name   => 'SCHEMA_EXPR',
        value  => 'IN (''MUSIC_APP_V2'')'
    );

    DBMS_DATAPUMP.METADATA_FILTER(
        handle      => job_handle,
        name        => 'NAME_EXPR',
        value       => 'NOT IN (''LOCAL_AUDIO_FILES'', ''HOSTED_AUDIO_FILES'')',
        object_type => 'TABLE'
    );

    DBMS_DATAPUMP.SET_PARAMETER(
        handle => job_handle,
        name   => 'INCLUDE_METADATA',
        value  => 0
    );

    DBMS_DATAPUMP.START_JOB(job_handle);
    DBMS_DATAPUMP.WAIT_FOR_JOB(job_handle, job_state);
    DBMS_OUTPUT.PUT_LINE('Data Pump job state: ' || job_state);
EXCEPTION
    WHEN OTHERS THEN
        error_message := SQLERRM;
        BEGIN
            DBMS_DATAPUMP.STOP_JOB(job_handle, immediate => 1);
        EXCEPTION
            WHEN OTHERS THEN
                NULL;
        END;
        RAISE_APPLICATION_ERROR(-20000, error_message);
END;
/
