package get_subscriptions_by_user_get

import (
	"context"
	"db_api/pkg/db"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

type Handler struct {
    DB *db.DB
}

func (h *Handler) Handle(w http.ResponseWriter, r *http.Request) {
    telegramIDStr := r.URL.Query().Get("telegram_id")
    if telegramIDStr == "" {
        http.Error(w, "missing telegram_id parameter", http.StatusBadRequest)
        return
    }

    telegramID, err := strconv.ParseInt(telegramIDStr, 10, 64)
    if err != nil {
        http.Error(w, "invalid telegram_id parameter", http.StatusBadRequest)
        return
    }

    ctx := context.Background()

	userID, err := h.DB.GetUserIDByTelegramID(ctx, telegramID)
	if err != nil {
		if strings.Contains(err.Error(), "no rows") {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]interface{}{
				"subscriptions": []interface{}{},
			})
			return
		}
		http.Error(w, "failed to find user by telegram_id: "+err.Error(), http.StatusInternalServerError)
		return
	}

    subs, err := h.DB.GetUserSubscriptions(ctx, userID)
    if err != nil {
        http.Error(w, "failed to get subscriptions: "+err.Error(), http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "subscriptions": subs,
    })
}
