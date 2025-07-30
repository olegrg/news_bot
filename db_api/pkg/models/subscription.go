package models

type Subscription struct {
	UserID    int64                  `db:"user_id" json:"user_id"`
	ChannelID int64                  `db:"channel_id" json:"channel_id"`
	Policy    map[string]interface{} `db:"policy" json:"policy"`
}

type ChannelOffset struct {
	ChannelID       int64  `json:"channel_id" db:"channel_id"`
	Link            string `json:"link" db:"link"`
	OffsetMessageID int64  `json:"offset_message_id" db:"offset_message_id"`
}
