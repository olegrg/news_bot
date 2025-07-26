package add_post_po

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
	defer r.Body.Close()

	var post models.Post
	if err := json.NewDecoder(r.Body).Decode(&post); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}

	ctx := context.Background()

	id, err := h.DB.GetOrCreatePost(ctx, &post)
	if err != nil {
		http.Error(w, "failed to get or create post: "+err.Error(), http.StatusInternalServerError)
		return
	}

	resp := map[string]interface{}{
		"id":      id,
		"message": "post created or already exists",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
