-- Initial schema for the music recommendation study app.
-- albums is intentionally omitted for now because the current use case
-- focuses on tracks, artists, play history, and recommendation logic.

CREATE TABLE artists (
    artist_id      NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_artists_normalized_name UNIQUE (normalized_name)
);

CREATE TABLE tracks (
    track_id          NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title             VARCHAR(255) NOT NULL,
    normalized_title  VARCHAR(255) NOT NULL,
    artist_id         NUMBER(19),
    duration_sec      INTEGER,
    local_file_count  INTEGER DEFAULT 0 NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_tracks_artist
        FOREIGN KEY (artist_id) REFERENCES artists (artist_id)
);

CREATE INDEX idx_tracks_artist_id ON tracks (artist_id);
CREATE INDEX idx_tracks_normalized_title ON tracks (normalized_title);

CREATE TABLE play_history_youtube (
    youtube_play_id      NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id             NUMBER(19),
    raw_title            VARCHAR(255) NOT NULL,
    raw_artist           VARCHAR(255),
    normalized_title     VARCHAR(255),
    normalized_artist    VARCHAR(255),
    played_at            TIMESTAMP NOT NULL,
    skipped_flag         NUMBER(1) DEFAULT 0 NOT NULL,
    matched_status       VARCHAR(30) DEFAULT 'unmatched' NOT NULL,
    source_payload       CLOB,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_play_history_youtube_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT ck_play_history_youtube_status
        CHECK (matched_status IN ('unmatched', 'matched', 'ignored')),
    CONSTRAINT ck_play_history_youtube_skipped
        CHECK (skipped_flag IN (0, 1))
);

CREATE INDEX idx_play_history_youtube_played_at
    ON play_history_youtube (played_at);
CREATE INDEX idx_play_history_youtube_track_id
    ON play_history_youtube (track_id);

CREATE TABLE play_history_sony (
    sony_play_id         NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id             NUMBER(19),
    raw_title            VARCHAR(255) NOT NULL,
    raw_artist           VARCHAR(255),
    normalized_title     VARCHAR(255),
    normalized_artist    VARCHAR(255),
    played_at            TIMESTAMP NOT NULL,
    skipped_flag         NUMBER(1) DEFAULT 0 NOT NULL,
    matched_status       VARCHAR(30) DEFAULT 'unmatched' NOT NULL,
    source_payload       CLOB,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_play_history_sony_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT ck_play_history_sony_status
        CHECK (matched_status IN ('unmatched', 'matched', 'ignored')),
    CONSTRAINT ck_play_history_sony_skipped
        CHECK (skipped_flag IN (0, 1))
);

CREATE INDEX idx_play_history_sony_played_at
    ON play_history_sony (played_at);
CREATE INDEX idx_play_history_sony_track_id
    ON play_history_sony (track_id);

CREATE TABLE track_features (
    track_feature_id   NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id           NUMBER(19) NOT NULL,
    bpm                DECIMAL(6,2),
    musical_key        VARCHAR(20),
    energy_level       VARCHAR(50),
    mood               VARCHAR(100),
    genre              VARCHAR(100),
    feature_source     VARCHAR(50),
    analyzed_at        TIMESTAMP,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_track_features_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT uq_track_features_track UNIQUE (track_id)
);

CREATE TABLE track_tags (
    track_tag_id       NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id           NUMBER(19) NOT NULL,
    tag_name           VARCHAR(100) NOT NULL,
    tag_value          VARCHAR(255),
    tag_source         VARCHAR(50),
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_track_tags_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id)
);

CREATE INDEX idx_track_tags_track_id ON track_tags (track_id);
CREATE INDEX idx_track_tags_name ON track_tags (tag_name);

CREATE TABLE recommendation_logs (
    recommendation_log_id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recommended_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    recommendation_type   VARCHAR(50) NOT NULL,
    based_on_source       VARCHAR(50) NOT NULL,
    target_track_id       NUMBER(19),
    score                 DECIMAL(10,4),
    reason_text           VARCHAR(1000),
    rule_json             CLOB,
    CONSTRAINT fk_recommendation_logs_track
        FOREIGN KEY (target_track_id) REFERENCES tracks (track_id)
);

CREATE INDEX idx_recommendation_logs_recommended_at
    ON recommendation_logs (recommended_at);
