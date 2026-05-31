-- Delete only the three rows inserted by 004_seed_cloud_smoke_test.sql.

SET DEFINE OFF

BEGIN
    FOR sample IN (
        SELECT track_source_id, track_id
        FROM track_sources
        WHERE source_track_id LIKE 'cloud-smoke-test-%'
    ) LOOP
        FOR sample_artist IN (
            SELECT artist_id
            FROM track_artists
            WHERE track_id = sample.track_id
        ) LOOP
        DELETE FROM recommendation_items
        WHERE track_source_id = sample.track_source_id
           OR track_id = sample.track_id;

        DELETE FROM play_events
        WHERE track_source_id = sample.track_source_id
           OR track_id = sample.track_id;

        DELETE FROM hosted_audio_files
        WHERE track_source_id = sample.track_source_id;

        DELETE FROM track_features
        WHERE track_id = sample.track_id;

        DELETE FROM track_tags
        WHERE track_id = sample.track_id;

        DELETE FROM track_artists
        WHERE track_id = sample.track_id;

        DELETE FROM track_sources
        WHERE track_source_id = sample.track_source_id;

        DELETE FROM tracks
        WHERE track_id = sample.track_id;

        DELETE FROM artists
        WHERE artist_id = sample_artist.artist_id
          AND NOT EXISTS (
              SELECT 1
              FROM track_artists ta
              WHERE ta.artist_id = sample_artist.artist_id
          );
        END LOOP;
    END LOOP;
END;
/

COMMIT;

SELECT COUNT(*) AS remaining_cloud_smoke_test_rows
FROM track_sources
WHERE source_track_id LIKE 'cloud-smoke-test-%';
