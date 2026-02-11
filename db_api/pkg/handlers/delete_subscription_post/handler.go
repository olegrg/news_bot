package delete_subscription_post

import (
    "context"
    "db_api/pkg/db"
    "encoding/json"
    "net/http"
)

type Handler struct {
    DB *db.DB
}

type Request struct {
    UserTelegramID    int64 `json:"user_telegram_id"`
    ChannelTelegramID int64 `json:"channel_telegram_id"`
}

func (h *Handler) Handle(w http.ResponseWriter, r *http.Request) {
    var req Request
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "invalid request body", http.StatusBadRequest)
        return
    }
    defer r.Body.Close()

    ctx := context.Background()

    userID, err := h.DB.GetUserIDByTelegramID(ctx, req.UserTelegramID)
    if err != nil {
        http.Error(w, "failed to find user by telegram_id: "+err.Error(), http.StatusInternalServerError)
        return
    }

    channelID, err := h.DB.GetChannelIDByTelegramID(ctx, req.ChannelTelegramID)
    if err != nil {
        http.Error(w, "failed to find channel by telegram_id: "+err.Error(), http.StatusInternalServerError)
        return
    }

    if err := h.DB.DeleteSubscription(ctx, userID, channelID); err != nil {
        http.Error(w, "failed to delete subscription: "+err.Error(), http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "message": "subscription deleted",
    })
}
