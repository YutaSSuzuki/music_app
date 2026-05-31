-- Three hosted tracks for the cloud smoke test.
-- Copy the corresponding audio files to the paths below before testing playback.

SET DEFINE OFF

DECLARE
    v_artist_id       artists.artist_id%TYPE;
    v_track_id        tracks.track_id%TYPE;
    v_track_source_id track_sources.track_source_id%TYPE;

    PROCEDURE add_sample_track (
        p_title           IN VARCHAR2,
        p_normalized_title IN VARCHAR2,
        p_artist          IN VARCHAR2,
        p_normalized_artist IN VARCHAR2,
        p_duration_sec    IN NUMBER,
        p_source_track_id IN VARCHAR2,
        p_file_path       IN VARCHAR2,
        p_file_size_bytes IN NUMBER
    ) IS
    BEGIN
        INSERT INTO artists (name, normalized_name)
        VALUES (p_artist, p_normalized_artist)
        RETURNING artist_id INTO v_artist_id;

        INSERT INTO tracks (title, normalized_title, duration_sec)
        VALUES (p_title, p_normalized_title, p_duration_sec)
        RETURNING track_id INTO v_track_id;

        INSERT INTO track_artists (track_id, artist_id)
        VALUES (v_track_id, v_artist_id);

        INSERT INTO track_sources (
            track_id,
            source_name,
            source_track_id,
            raw_title,
            raw_artist,
            normalized_title,
            normalized_artist,
            source_payload
        )
        VALUES (
            v_track_id,
            'local',
            p_source_track_id,
            p_title,
            p_artist,
            p_normalized_title,
            p_normalized_artist,
            '{"seed":"cloud-smoke-test"}'
        )
        RETURNING track_source_id INTO v_track_source_id;

        INSERT INTO hosted_audio_files (
            track_source_id,
            track_id,
            file_path_linux,
            file_size_bytes
        )
        VALUES (
            v_track_source_id,
            v_track_id,
            p_file_path,
            p_file_size_bytes
        );
    END;
BEGIN
    add_sample_track(
        '二人スケッチ',
        '二人スケッチ',
        'Rin''ca',
        'rin''ca',
        277,
        'cloud-smoke-test-001',
        '/data/music-app/audio/sample-001.m4a',
        4475110
    );

    add_sample_track(
        'ファイトソング',
        'ファイトソング',
        'Eve',
        'eve',
        209,
        'cloud-smoke-test-002',
        '/data/music-app/audio/sample-002.m4a',
        7558349
    );

    add_sample_track(
        'Girl meets Love',
        'girl meets love',
        '片霧烈火&鈴湯',
        '片霧烈火&鈴湯',
        253,
        'cloud-smoke-test-003',
        '/data/music-app/audio/sample-003.mp3',
        4057429
    );

    COMMIT;
END;
/

SELECT
    ts.source_track_id,
    t.title,
    a.name AS artist,
    haf.file_path_linux,
    haf.file_size_bytes
FROM track_sources ts
JOIN tracks t ON t.track_id = ts.track_id
JOIN track_artists ta ON ta.track_id = t.track_id
JOIN artists a ON a.artist_id = ta.artist_id
JOIN hosted_audio_files haf ON haf.track_source_id = ts.track_source_id
WHERE ts.source_track_id LIKE 'cloud-smoke-test-%'
ORDER BY ts.source_track_id;
