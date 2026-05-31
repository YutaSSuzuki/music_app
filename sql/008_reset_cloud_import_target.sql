-- Reset the cloud DB before retrying a DATA_ONLY import.
-- Run only on the new Oracle EC2 DB. This deletes all application data.

ALTER TABLE hosted_audio_files DISABLE CONSTRAINT fk_hosted_audio_source;
ALTER TABLE hosted_audio_files DISABLE CONSTRAINT fk_hosted_audio_track;
ALTER TABLE play_events DISABLE CONSTRAINT fk_play_events_track;
ALTER TABLE play_events DISABLE CONSTRAINT fk_play_events_track_source;
ALTER TABLE recommendation_items DISABLE CONSTRAINT fk_recommendation_items_run;
ALTER TABLE recommendation_items DISABLE CONSTRAINT fk_recommendation_items_source;
ALTER TABLE recommendation_items DISABLE CONSTRAINT fk_recommendation_items_track;
ALTER TABLE track_artists DISABLE CONSTRAINT fk_track_artists_artist;
ALTER TABLE track_artists DISABLE CONSTRAINT fk_track_artists_track;
ALTER TABLE track_features DISABLE CONSTRAINT fk_track_features_track;
ALTER TABLE track_sources DISABLE CONSTRAINT fk_track_sources_track;
ALTER TABLE track_tags DISABLE CONSTRAINT fk_track_tags_track;

TRUNCATE TABLE hosted_audio_files;
TRUNCATE TABLE recommendation_items;
TRUNCATE TABLE play_events;
TRUNCATE TABLE track_tags;
TRUNCATE TABLE track_features;
TRUNCATE TABLE track_artists;
TRUNCATE TABLE track_sources;
TRUNCATE TABLE recommendation_runs;
TRUNCATE TABLE tracks;
TRUNCATE TABLE artists;

SELECT 'ARTISTS' AS table_name, COUNT(*) AS row_count FROM artists
UNION ALL
SELECT 'TRACKS', COUNT(*) FROM tracks
UNION ALL
SELECT 'TRACK_ARTISTS', COUNT(*) FROM track_artists
UNION ALL
SELECT 'TRACK_SOURCES', COUNT(*) FROM track_sources
UNION ALL
SELECT 'HOSTED_AUDIO_FILES', COUNT(*) FROM hosted_audio_files
UNION ALL
SELECT 'PLAY_EVENTS', COUNT(*) FROM play_events
UNION ALL
SELECT 'RECOMMENDATION_RUNS', COUNT(*) FROM recommendation_runs
UNION ALL
SELECT 'RECOMMENDATION_ITEMS', COUNT(*) FROM recommendation_items;
