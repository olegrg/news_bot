package add_subscription_post

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

type Request struct {
	User    models.User    `json:"user"`
	Channel models.Channel `json:"channel"`
}

func (h *Handler) Handle(w http.ResponseWriter, r *http.Request) {
	var req Request
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	ctx := context.Background()

	userID, err := h.DB.GetOrCreateUser(ctx, &req.User)
	if err != nil {
		http.Error(w, "failed to create or get user: "+err.Error(), http.StatusInternalServerError)
		return
	}

	channelID, err := h.DB.GetOrCreateChannel(ctx, &req.Channel)
	if err != nil {
		http.Error(w, "failed to create or get channel: "+err.Error(), http.StatusInternalServerError)
		return
	}

	_, err = h.DB.GetOrCreateSubscription(ctx, &models.Subscription{
		UserID:    userID,
		ChannelID: channelID,
	})
	if err != nil {
		http.Error(w, "failed to create subscription: "+err.Error(), http.StatusInternalServerError)
		return
	}

	resp := map[string]interface{}{
		"user_id":    userID,
		"channel_id": channelID,
		"message":    "subscription created or updated",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
