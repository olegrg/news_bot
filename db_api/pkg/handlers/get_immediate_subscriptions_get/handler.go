package get_immediate_subscriptions_get

import (
    "context"
    "db_api/pkg/db"
    "encoding/json"
    "net/http"
)

type Handler struct {
    DB *db.DB
}

func (h *Handler) Handle(w http.ResponseWriter, r *http.Request) {
    ctx := context.Background()

    subs, err := h.DB.GetImmediateSubscriptions(ctx)
    if err != nil {
        http.Error(w, "failed to get immediate subscriptions: "+err.Error(), http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "subscriptions": subs,
    })
}
