from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `child` (
    `child_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `birth_date` DATE NOT NULL,
    `weight_kg` DECIMAL(5,2),
    `allergies` LONGTEXT,
    `notes` LONGTEXT,
    `consent_agreed_at` DATETIME(6) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `guardian_id` BIGINT NOT NULL,
    CONSTRAINT `fk_child_guardian_238177c7` FOREIGN KEY (`guardian_id`) REFERENCES `guardian` (`guardian_id`) ON DELETE CASCADE,
    KEY `idx_child_guardia_bebf71` (`guardian_id`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `prescription` (
    `prescription_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `source_type` VARCHAR(20) NOT NULL COMMENT 'PRESCRIPTION: PRESCRIPTION\nPILL_BAG: PILL_BAG',
    `status` VARCHAR(20) NOT NULL COMMENT 'UPLOADED: UPLOADED\nOCR_DONE: OCR_DONE\nCONFIRMED: CONFIRMED\nGUIDE_DONE: GUIDE_DONE\nFAILED: FAILED' DEFAULT 'UPLOADED',
    `prescription_date` DATE,
    `hospital_name` VARCHAR(100),
    `diagnosis_extracted` VARCHAR(20),
    `diagnosis_user_input` VARCHAR(200),
    `symptom_notes` LONGTEXT,
    `image_storage_key` VARCHAR(512),
    `raw_text_masked` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `child_id` BIGINT NOT NULL,
    CONSTRAINT `fk_prescrip_child_48905120` FOREIGN KEY (`child_id`) REFERENCES `child` (`child_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `guide` (
    `guide_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guide_content` JSON NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `prescription_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_guide_prescrip_94835305` FOREIGN KEY (`prescription_id`) REFERENCES `prescription` (`prescription_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `medication` (
    `medication_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `insurance_code` VARCHAR(20),
    `dose_per_time` DECIMAL(7,2),
    `unit` VARCHAR(10),
    `daily_count` SMALLINT,
    `total_days` SMALLINT,
    `as_needed` BOOL NOT NULL DEFAULT 0,
    `max_daily_count` SMALLINT,
    `usage` VARCHAR(100),
    `route` VARCHAR(10) COMMENT 'ORAL: ORAL\nEXTERNAL: EXTERNAL',
    `dosage_form` VARCHAR(20) COMMENT 'SYRUP: SYRUP\nDRY_SYRUP: DRY_SYRUP\nPOWDER: POWDER\nTABLET: TABLET\nCAPSULE: CAPSULE\nOINTMENT: OINTMENT\nCREAM: CREAM\nEYE_DROP: EYE_DROP\nSUPPOSITORY: SUPPOSITORY\nETC: ETC',
    `confidence` DECIMAL(3,2),
    `ocr_value_snapshot` JSON,
    `is_user_edited` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `prescription_id` BIGINT NOT NULL,
    CONSTRAINT `fk_medicati_prescrip_cc36817c` FOREIGN KEY (`prescription_id`) REFERENCES `prescription` (`prescription_id`) ON DELETE CASCADE,
    KEY `idx_medication_prescri_4ce762` (`prescription_id`)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `child`;
        DROP TABLE IF EXISTS `medication`;
        DROP TABLE IF EXISTS `prescription`;
        DROP TABLE IF EXISTS `guide`;"""


MODELS_STATE = (
    "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"
    "QyZO6loR8D5926zavxw4bsh2H77/8HPj+i4w=="
)
