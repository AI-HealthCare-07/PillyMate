from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `guardian` (
    `guardian_id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `email` VARCHAR(255) NOT NULL UNIQUE COMMENT '소문자 정규화 저장',
    `password_hash` VARCHAR(255) NOT NULL COMMENT 'bcrypt 해시',
    `name` VARCHAR(50) NOT NULL,
    `birth_date` DATE NOT NULL COMMENT '가입 시 만 19세 이상 서버 검증',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4 COMMENT='보호자';
        DROP TABLE IF EXISTS `users`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `guardian`;"""


MODELS_STATE = (
    "eJztl21vm0gQx78K4lUq5SzAYPC9s+Nc6tPFOaXu3alNRZfdNUaBxYWlqVXlu9/MYsDghy"
    "ZVdEmkU6QY/2d2mfnt7M76u56kjMd5b8SziC71X7XvuiAJh4eO5VTTyWrV6ChIEsTKlTQ+"
    "QS4zQiWoCxLnHCTGc5pFKxmlAlRRxDGKKQXHSISNVIjoS8F9mYZcLnkGho+fQI4E4994Xn"
    "1d3fqLiMesFWrE8N1K9+V6pbSpkL8pR3xb4NM0LhLROK/WcpmK2jsSEtWQC54RyXF6mRUY"
    "Pka3ybPKqIy0cSlD3BrD+IIUsdxK94EMaCqQH0STqwRDfMsvlmm7ttcf2B64qEhqxb0v02"
    "tyLwcqArO5fq/sRJLSQ2FsuH3lWY4h7cA7W5JsP72tIR2EEHgXYQXsGMNKaCA2hfNEFBPy"
    "zY+5CCUWuOU4R5j9Nbo+ezu6PgGvN5hNCsVc1vhsY7JKG4JtQOLWeATEjfvrBGgaxgMAgt"
    "dBgMrWBghvlLzcg22Iv7+7mu2HuDWkA/K9gAQ/sojKUy2OcvnpZWI9QhGzxqCTPP8Sb8M7"
    "uRz90+V69sfVWFFIcxlmahY1wRgY45G5uN3a/CgEhN7ekYz5O5bUSg/57poSK+kqRJBQsc"
    "KMMb9NE7koYIqIiH0NprYdbTHhttePmox+UwR0Yd8UbND3bgrqDg29syR7XLST8+uJ9tXs"
    "GZrVM7WL96PryXQ0e9O7EfBX0IUD7oHNKDw7zID/pgnPgTW0tc9VfL2IfQbNc6gGDvYC3A"
    "jlxqk2GaPAOY5wF8rqujjh0LPx2TY0eD187xvGZoJ6Ur+c1OJ2T3/6TjmOwoPNciuC19Y1"
    "h5bV77uW0R94ju26jmfU7XPXdKyPjqcX2Epbm+7HvZUnJIof0xTqAU/TFn6Sso5l7WGRBv"
    "W+gA/PdKCQGdY+Gzi2krBOqUuc7tZ6ti68Inl+l8JZtST58jHodwY+c2fWA5qtVxIoMwfP"
    "CGox+mIoq89HwK38X+dtx3nIZcc5fNdxdq46QZTJpQ/nxh6KE1D3U2yP6rBEWUYJ71X2/6"
    "5Ssb2VB4HnaGWlatjUKNXMIZ4lfa9uddSgpla3TerhMULgHAFpOGQPK/AjqzEZzc+718qM"
    "IwWf7LlZTjbQDtwuWyOP8caHF1rJkAO7EvF6c/ofYTefXp6/m48u/2zdOpEoWiylrjvqya"
    "BT9fUk2t/T+VsNv2ofrmbn3ctp7Tf/oGNMpJCpL9I7HxpM06gqtQLTWthixX5yYdsj/1/Y"
    "Z11YFfyz/ka5/xeplAzr"
)
