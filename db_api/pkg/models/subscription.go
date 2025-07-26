package models

type Subscription struct {
	UserID    int64                  `db:"user_id" json:"user_id"`
	ChannelID int64                  `db:"channel_id" json:"channel_id"`
	Policy    map[string]interface{} `db:"policy" json:"policy"`
}
