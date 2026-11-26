from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `medication_dose_log` (
    `dose_log_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `dose_date` DATE NOT NULL COMMENT '먹인 날 (KST)',
    `slot` VARCHAR(10) NOT NULL COMMENT '먹는 때: 아침·점심·저녁·자기 전',
    `is_taken` BOOL NOT NULL COMMENT 'true 먹임 / false 안 먹임',
    `checked_at` DATETIME(6) NOT NULL COMMENT '마지막으로 체크하거나 취소한 시각' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `medication_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_medication__medicat_1b9f57` (`medication_id`, `dose_date`, `slot`),
    CONSTRAINT `fk_medicati_medicati_fdd5272e` FOREIGN KEY (`medication_id`) REFERENCES `medication` (`medication_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='복약 체크 기록';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `medication_dose_log`;"""


MODELS_STATE = (
    "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"
)
