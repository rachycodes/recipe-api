# Acceptance list

- POST /register → 201 on success, returns ...
- POST /login → 200 on success, returns token and user
- GET /recipes → 200 with list of recipes when authorized
- DELETE /recipes/<id> 204 on success
- PUT /recipes/<id> 200 on success

## Single-file costs

- Difficult to find what you need in a long code file
- Making changes without side effects 
- Testing only one part of the app

## Target package layout (plan)

- Routes = “Flask endpoints & HTTP details”
- Authentication = "get owner/admin status"
- Services = “business logic”
- Data = “DB access”

app/
 auth/
  routes.py
  services.py
  data.py
 recipes/
  routes.py
  services.py
  data.py
 config.py        # configuration (DB path, secrets, etc.)
 wsgi.py