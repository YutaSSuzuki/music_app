-- Revised schema for bidirectional music recommendation.
--
-- Design goals:
-- - YouTube Music history can recommend local files.
-- - Local playback history can recommend YouTube Music tracks later.
-- - Play history is stored in one table regardless of source.
-- - Recommendation results point to real candidate tracks and sources.

CREATE TABLE artists (
    artist_id        NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             VARCHAR(255) NOT NULL,
    normalized_name  VARCHAR(255) NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_artists_normalized_name UNIQUE (normalized_name)
);

CREATE TABLE tracks (
    track_id          NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title             VARCHAR(255) NOT NULL,
    normalized_title  VARCHAR(255) NOT NULL,
    duration_sec      INTEGER,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_tracks_normalized_title ON tracks (normalized_title);

CREATE TABLE track_artists (
    track_artist_id  NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id         NUMBER(19) NOT NULL,
    artist_id        NUMBER(19) NOT NULL,
    artist_role      VARCHAR(50) DEFAULT 'primary' NOT NULL,
    artist_order     INTEGER DEFAULT 1 NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_track_artists_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT fk_track_artists_artist
        FOREIGN KEY (artist_id) REFERENCES artists (artist_id),
    CONSTRAINT uq_track_artists_role_order
        UNIQUE (track_id, artist_role, artist_order)
);

CREATE INDEX idx_track_artists_track_id ON track_artists (track_id);
CREATE INDEX idx_track_artists_artist_id ON track_artists (artist_id);

CREATE TABLE track_sources (
    track_source_id    NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id           NUMBER(19) NOT NULL,
    source_name        VARCHAR(50) NOT NULL,
    source_track_id    VARCHAR(255),
    source_url         VARCHAR(1000),
    raw_title          VARCHAR(255),
    raw_artist         VARCHAR(255),
    normalized_title   VARCHAR(255),
    normalized_artist  VARCHAR(255),
    availability_status VARCHAR(30) DEFAULT 'available' NOT NULL,
    match_confidence   DECIMAL(5,4),
    source_payload     CLOB,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_track_sources_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT ck_track_sources_source
        CHECK (source_name IN ('local', 'youtube_music', 'sony_music_center')),
    CONSTRAINT ck_track_sources_availability
        CHECK (availability_status IN ('available', 'missing', 'unknown'))
);

CREATE INDEX idx_track_sources_track_id ON track_sources (track_id);
CREATE INDEX idx_track_sources_source ON track_sources (source_name);
CREATE INDEX idx_track_sources_normalized
    ON track_sources (source_name, normalized_title, normalized_artist);

CREATE TABLE local_audio_files (
    local_audio_file_id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_source_id     NUMBER(19) NOT NULL,
    track_id            NUMBER(19) NOT NULL,
    file_path_linux     VARCHAR(2000) NOT NULL,
    file_path_windows   VARCHAR(2000),
    file_name           VARCHAR(500),
    file_ext            VARCHAR(30),
    file_size_bytes     NUMBER(19),
    modified_at         TIMESTAMP,
    file_hash           VARCHAR(128),
    is_available        NUMBER(1) DEFAULT 1 NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_local_audio_files_source
        FOREIGN KEY (track_source_id) REFERENCES track_sources (track_source_id),
    CONSTRAINT fk_local_audio_files_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT uq_local_audio_files_path UNIQUE (file_path_linux),
    CONSTRAINT ck_local_audio_files_available CHECK (is_available IN (0, 1))
);

CREATE INDEX idx_local_audio_files_track_id ON local_audio_files (track_id);

CREATE TABLE play_events (
    play_event_id      NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name        VARCHAR(50) NOT NULL,
    track_id           NUMBER(19),
    track_source_id    NUMBER(19),
    raw_title          VARCHAR(255) NOT NULL,
    raw_artist         VARCHAR(255),
    normalized_title   VARCHAR(255),
    normalized_artist  VARCHAR(255),
    played_at          TIMESTAMP NOT NULL,
    skipped_flag       NUMBER(1) DEFAULT 0 NOT NULL,
    match_status       VARCHAR(30) DEFAULT 'unmatched' NOT NULL,
    source_url         VARCHAR(1000),
    source_payload     CLOB,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_play_events_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT fk_play_events_track_source
        FOREIGN KEY (track_source_id) REFERENCES track_sources (track_source_id),
    CONSTRAINT ck_play_events_source
        CHECK (source_name IN ('local', 'youtube_music', 'sony_music_center')),
    CONSTRAINT ck_play_events_skipped
        CHECK (skipped_flag IN (0, 1)),
    CONSTRAINT ck_play_events_match_status
        CHECK (match_status IN ('unmatched', 'matched', 'ignored'))
);

CREATE INDEX idx_play_events_source_played_at
    ON play_events (source_name, played_at);
CREATE INDEX idx_play_events_track_id ON play_events (track_id);
CREATE INDEX idx_play_events_normalized
    ON play_events (source_name, normalized_title, normalized_artist);

CREATE TABLE track_features (
    track_feature_id  NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id          NUMBER(19) NOT NULL,
    bpm               DECIMAL(6,2),
    musical_key       VARCHAR(20),
    energy_level      VARCHAR(50),
    mood              VARCHAR(100),
    genre             VARCHAR(100),
    feature_source    VARCHAR(50),
    analyzed_at       TIMESTAMP,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_track_features_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT uq_track_features_track UNIQUE (track_id)
);

CREATE TABLE track_tags (
    track_tag_id  NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id      NUMBER(19) NOT NULL,
    tag_name      VARCHAR(100) NOT NULL,
    tag_value     VARCHAR(255),
    tag_source    VARCHAR(50),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_track_tags_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id)
);

CREATE INDEX idx_track_tags_track_id ON track_tags (track_id);
CREATE INDEX idx_track_tags_name ON track_tags (tag_name);

CREATE TABLE recommendation_runs (
    recommendation_run_id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recommended_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    recommendation_type   VARCHAR(50) NOT NULL,
    input_source          VARCHAR(50) NOT NULL,
    target_source         VARCHAR(50) NOT NULL,
    model_name            VARCHAR(100),
    prompt_json           CLOB,
    context_json          CLOB,
    result_json           CLOB,
    CONSTRAINT ck_recommendation_runs_input
        CHECK (input_source IN ('local', 'youtube_music', 'sony_music_center')),
    CONSTRAINT ck_recommendation_runs_target
        CHECK (target_source IN ('local', 'youtube_music', 'sony_music_center'))
);

CREATE INDEX idx_recommendation_runs_recommended_at
    ON recommendation_runs (recommended_at);
CREATE INDEX idx_recommendation_runs_sources
    ON recommendation_runs (input_source, target_source);

CREATE TABLE recommendation_items (
    recommendation_item_id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recommendation_run_id  NUMBER(19) NOT NULL,
    rank_no                INTEGER NOT NULL,
    track_id               NUMBER(19) NOT NULL,
    track_source_id        NUMBER(19),
    score                  DECIMAL(10,4),
    reason_text            VARCHAR(1000),
    item_json              CLOB,
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_recommendation_items_run
        FOREIGN KEY (recommendation_run_id)
        REFERENCES recommendation_runs (recommendation_run_id),
    CONSTRAINT fk_recommendation_items_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT fk_recommendation_items_source
        FOREIGN KEY (track_source_id) REFERENCES track_sources (track_source_id),
    CONSTRAINT uq_recommendation_items_rank
        UNIQUE (recommendation_run_id, rank_no)
);

CREATE INDEX idx_recommendation_items_run_id
    ON recommendation_items (recommendation_run_id);
CREATE INDEX idx_recommendation_items_track_id
    ON recommendation_items (track_id);
