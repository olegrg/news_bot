package models

import "time"

type Post struct {
	ID          int64     `db:"id" json:"id"`
	MessageID   int64     `db:"message_id" json:"message_id"`
	ChannelID   int64     `db:"channel_id" json:"channel_id"`
	PublishedAt time.Time `db:"published_at" json:"published_at"` // или time.Time
	Content     string    `db:"content" json:"content"`
	Views       int       `db:"views" json:"views"`
	Reactions   int       `db:"reactions" json:"reactions"` // количество реакций
	Comments    int       `db:"comments" json:"comments"`   // количество комментариев
	Forwards    int       `db:"forwards" json:"forwards"`
	Score       float64   `db:"score" json:"score"`
	CreatedAt   time.Time `db:"created_at" json:"created_at"` // или time.Time
}

type ScoredPost struct {
	Link       string  `json:"link" db:"link"`
	MessageIDs []int64 `db:"message_id" json:"message_ids"`
}
