CREATE TABLE hosted_audio_files (
    hosted_audio_file_id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_source_id      NUMBER(19) NOT NULL,
    track_id             NUMBER(19) NOT NULL,
    file_path_linux      VARCHAR2(2000) NOT NULL,
    file_size_bytes      NUMBER(19),
    file_hash            VARCHAR2(128),
    is_available         NUMBER(1) DEFAULT 1 NOT NULL,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_hosted_audio_source
        FOREIGN KEY (track_source_id) REFERENCES track_sources (track_source_id),
    CONSTRAINT fk_hosted_audio_track
        FOREIGN KEY (track_id) REFERENCES tracks (track_id),
    CONSTRAINT uq_hosted_audio_source UNIQUE (track_source_id),
    CONSTRAINT uq_hosted_audio_path UNIQUE (file_path_linux),
    CONSTRAINT ck_hosted_audio_available CHECK (is_available IN (0, 1))
);

CREATE INDEX idx_hosted_audio_track_id ON hosted_audio_files (track_id);
