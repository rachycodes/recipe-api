# Security notes – open API baseline

- 2026-11-17:
  - Anonymous `GET /recipes` returns all recipes, including one with `"is_public": false` (`"Secret family hot sauce"`).
  - Anonymous `POST /recipes` successfully creates a new recipe (observed with `id: 4`).
  - Anonymous `DELETE /recipes/4` permanently deletes recipe 4 (it no longer appears in `GET /recipes`).