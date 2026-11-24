from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `child` (
    `child_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `birth_date` DATE NOT NULL COMMENT '만 18세 미만만 허용 (서버 검증)',
    `weight_kg` DECIMAL(5,2) COMMENT '0.5 ~ 150.0',
    `allergies` LONGTEXT,
    `notes` LONGTEXT,
    `consent_agreed_at` DATETIME(6) NOT NULL COMMENT '보호자 동의 3항목 완료 시각',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `guardian_id` BIGINT NOT NULL,
    CONSTRAINT `fk_child_guardian_238177c7` FOREIGN KEY (`guardian_id`) REFERENCES `guardian` (`guardian_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='자녀';
        CREATE TABLE IF NOT EXISTS `prescription` (
    `prescription_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `source_type` VARCHAR(20) NOT NULL COMMENT 'PRESCRIPTION: PRESCRIPTION\nPILL_BAG: PILL_BAG',
    `status` VARCHAR(20) NOT NULL COMMENT 'UPLOADED: UPLOADED\nOCR_DONE: OCR_DONE\nCONFIRMED: CONFIRMED\nGUIDE_DONE: GUIDE_DONE\nFAILED: FAILED',
    `prescription_date` DATE COMMENT '처방전 교부일. 약봉투는 항상 NULL',
    `hospital_name` VARCHAR(100),
    `diagnosis_extracted` VARCHAR(50) COMMENT 'OCR 질병분류기호 쉼표 연결 (참고용). 약봉투는 항상 NULL',
    `diagnosis_user_input` VARCHAR(200) COMMENT '보호자 입력 병명. CONFIRMED/GUIDE_DONE 시 필수·비공백',
    `symptom_notes` LONGTEXT,
    `image_storage_key` VARCHAR(512) COMMENT 'S3 키. 가이드 생성 후 NULL',
    `raw_text_masked` LONGTEXT COMMENT '마스킹된 OCR 원문. API 응답·로그 노출 금지',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `child_id` BIGINT NOT NULL,
    CONSTRAINT `fk_prescrip_child_48905120` FOREIGN KEY (`child_id`) REFERENCES `child` (`child_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='처방전';
        CREATE TABLE IF NOT EXISTS `medication` (
    `medication_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `insurance_code` VARCHAR(20) COMMENT '처방전 9자리. 약봉투는 항상 NULL',
    `dose_per_time` DECIMAL(8,4),
    `unit` VARCHAR(10) COMMENT 'ML: mL\nPACKET: 포\nTABLET: 정\nCAPSULE: 캡슐\nGRAM: g\nDROP: 방울\nPIECE: 개',
    `daily_count` TINYINT COMMENT 'as_needed=1이면 NULL',
    `total_days` SMALLINT,
    `as_needed` BOOL NOT NULL DEFAULT 0,
    `max_daily_count` TINYINT COMMENT '필요시 약 확정 시 필수 (앱 검증)',
    `usage` VARCHAR(100),
    `route` VARCHAR(10) COMMENT 'ORAL: ORAL\nEXTERNAL: EXTERNAL',
    `dosage_form` VARCHAR(20) COMMENT 'SYRUP: SYRUP\nDRY_SYRUP: DRY_SYRUP\nPOWDER: POWDER\nTABLET: TABLET\nCAPSULE: CAPSULE\nOINTMENT: OINTMENT\nCREAM: CREAM\nEYE_DROP: EYE_DROP\nSUPPOSITORY: SUPPOSITORY\nETC: ETC',
    `confidence` DECIMAL(3,2) COMMENT '0.00 ~ 1.00',
    `ocr_value_snapshot` JSON COMMENT '최초 OCR 불변 스냅샷 (run_ocr 약품 dict)',
    `is_user_edited` BOOL NOT NULL DEFAULT 0,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `prescription_id` BIGINT NOT NULL,
    CONSTRAINT `fk_medicati_prescrip_cc36817c` FOREIGN KEY (`prescription_id`) REFERENCES `prescription` (`prescription_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='처방 약품';
        CREATE TABLE IF NOT EXISTS `guide` (
    `guide_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guide_content` JSON NOT NULL COMMENT 'summary, medications, warning_signs, care_tips, disclaimer 5개 고정 키',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `prescription_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_guide_prescrip_94835305` FOREIGN KEY (`prescription_id`) REFERENCES `prescription` (`prescription_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='맞춤형 복약 가이드';
        CREATE TABLE IF NOT EXISTS `push_token` (
    `push_token_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `token` VARCHAR(512) NOT NULL UNIQUE,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `guardian_id` BIGINT NOT NULL,
    CONSTRAINT `fk_push_tok_guardian_96a36d78` FOREIGN KEY (`guardian_id`) REFERENCES `guardian` (`guardian_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='웹 푸시 토큰';
        CREATE TABLE IF NOT EXISTS `medication_alarm` (
    `alarm_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `notify_time` TIME(6) NOT NULL,
    `start_date` DATE NOT NULL,
    `end_date` DATE NOT NULL COMMENT 'start_date + total_days - 1 (종료일 포함)',
    `is_enabled` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `medication_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_medication__medicat_253e6d` (`medication_id`, `notify_time`, `start_date`),
    CONSTRAINT `fk_medicati_medicati_f6a1a958` FOREIGN KEY (`medication_id`) REFERENCES `medication` (`medication_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='복약 알림 스케줄';
        -- ===== ERD v1.1 3절: Tortoise 모델로 표현할 수 없어 직접 추가 (aerich가 추적하지 않음) =====
        CREATE INDEX `idx_prescription_child_created` ON `prescription` (`child_id`, `created_at` DESC);
        ALTER TABLE `push_token` MODIFY `token` VARCHAR(512) NOT NULL COLLATE utf8mb4_bin;
        ALTER TABLE `child`
            ADD CONSTRAINT `chk_child_weight_kg` CHECK (`weight_kg` IS NULL OR `weight_kg` BETWEEN 0.5 AND 150.0);
        ALTER TABLE `prescription`
            ADD CONSTRAINT `chk_prescription_source_type` CHECK (`source_type` IN ('PRESCRIPTION', 'PILL_BAG')),
            ADD CONSTRAINT `chk_prescription_status`
                CHECK (`status` IN ('UPLOADED', 'OCR_DONE', 'CONFIRMED', 'GUIDE_DONE', 'FAILED')),
            ADD CONSTRAINT `chk_prescription_diagnosis` CHECK (
                `status` NOT IN ('CONFIRMED', 'GUIDE_DONE')
                OR (`diagnosis_user_input` IS NOT NULL AND CHAR_LENGTH(TRIM(`diagnosis_user_input`)) > 0)
            );
        ALTER TABLE `medication`
            ADD CONSTRAINT `chk_medication_unit` CHECK (`unit` IN ('mL', '포', '정', '캡슐', 'g', '방울', '개')),
            ADD CONSTRAINT `chk_medication_route` CHECK (`route` IN ('ORAL', 'EXTERNAL')),
            ADD CONSTRAINT `chk_medication_dosage_form` CHECK (`dosage_form` IN (
                'SYRUP', 'DRY_SYRUP', 'POWDER', 'TABLET', 'CAPSULE',
                'OINTMENT', 'CREAM', 'EYE_DROP', 'SUPPOSITORY', 'ETC'
            )),
            ADD CONSTRAINT `chk_medication_as_needed` CHECK (`as_needed` = FALSE OR `daily_count` IS NULL),
            ADD CONSTRAINT `chk_medication_confidence` CHECK (`confidence` IS NULL OR `confidence` BETWEEN 0 AND 1);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    # FK 참조 순서대로 자식 테이블부터 삭제
    return """
        DROP TABLE IF EXISTS `medication_alarm`;
        DROP TABLE IF EXISTS `guide`;
        DROP TABLE IF EXISTS `medication`;
        DROP TABLE IF EXISTS `prescription`;
        DROP TABLE IF EXISTS `child`;
        DROP TABLE IF EXISTS `push_token`;"""


MODELS_STATE = (
    "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"
    "wWNKG5Iv9Jne6gkl5YzXlBtSx/ebfvwPYatdzQ=="
)
