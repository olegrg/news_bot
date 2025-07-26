package add_user_post

import (
	"context"
	"db_api/pkg/db"
	"db_api/pkg/models"
	"encoding/json"
	"net/http"
)

type Handler struct {
	DB *db.DB
}

func (h *Handler) Handle(w http.ResponseWriter, r *http.Request) {
	var user models.User
	if err := json.NewDecoder(r.Body).Decode(&user); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}

	defer r.Body.Close()

	id, err := h.DB.AddUser(context.Background(), &user)
	if err != nil {
		http.Error(w, "failed to insert user: "+err.Error(), http.StatusInternalServerError)
		return
	}

	resp := map[string]interface{}{
		"id":      id,
		"message": "user created",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
