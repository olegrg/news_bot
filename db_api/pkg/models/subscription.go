package models

import "encoding/json"

type Subscription struct {
	UserID    int64                  `db:"user_id" json:"user_id"`
	ChannelID int64                  `db:"channel_id" json:"channel_id"`
	Policy    map[string]interface{} `db:"policy" json:"policy"`
}

type ChannelOffset struct {
	ChannelID       int64  `json:"channel_id" db:"channel_id"`
	TelegramID      int64  `json:"telegram_id" db:"telegram_id"`
	Link            string `json:"link" db:"link"`
	OffsetMessageID int64  `json:"offset_message_id" db:"offset_message_id"`
}

type ImmediateSubscription struct {
	UserTelegramID    int64  `json:"user_telegram_id" db:"user_telegram_id"`
	ChannelTelegramID int64  `json:"channel_telegram_id" db:"channel_telegram_id"`
	Link              string `json:"link" db:"link"`
}

type SubscriptionInfo struct {
	ChannelID       int64           `json:"channel_id" db:"channel_id"`
	ChannelTelegram int64           `json:"channel_telegram_id" db:"channel_telegram_id"`
	Title           string          `json:"title" db:"title"`
	Link            string          `json:"link" db:"link"`
	Policy          json.RawMessage `json:"policy" db:"policy"`
}
