-- Re-enable and validate foreign keys after the DATA_ONLY import.

ALTER TABLE track_artists ENABLE VALIDATE CONSTRAINT fk_track_artists_artist;
ALTER TABLE track_artists ENABLE VALIDATE CONSTRAINT fk_track_artists_track;
ALTER TABLE track_sources ENABLE VALIDATE CONSTRAINT fk_track_sources_track;
ALTER TABLE play_events ENABLE VALIDATE CONSTRAINT fk_play_events_track;
ALTER TABLE play_events ENABLE VALIDATE CONSTRAINT fk_play_events_track_source;
ALTER TABLE track_features ENABLE VALIDATE CONSTRAINT fk_track_features_track;
ALTER TABLE track_tags ENABLE VALIDATE CONSTRAINT fk_track_tags_track;
ALTER TABLE recommendation_items ENABLE VALIDATE CONSTRAINT fk_recommendation_items_run;
ALTER TABLE recommendation_items ENABLE VALIDATE CONSTRAINT fk_recommendation_items_source;
ALTER TABLE recommendation_items ENABLE VALIDATE CONSTRAINT fk_recommendation_items_track;
ALTER TABLE hosted_audio_files ENABLE VALIDATE CONSTRAINT fk_hosted_audio_source;
ALTER TABLE hosted_audio_files ENABLE VALIDATE CONSTRAINT fk_hosted_audio_track;

SELECT constraint_name, table_name, status, validated
FROM user_constraints
WHERE constraint_type = 'R'
ORDER BY table_name, constraint_name;
