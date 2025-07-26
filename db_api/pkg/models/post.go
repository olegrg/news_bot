package models

import "time"

type Post struct {
	ID          int64     `db:"id"`
	MessageID   int64     `db:"message_id"`
	ChannelID   int64     `db:"channel_id"`
	PublishedAt time.Time `db:"published_at"`
	Content     string    `db:"content"`
	Views       int       `db:"views"`
	Forwards    int       `db:"forwards"`
	Score       float64   `db:"score"`
	CreatedAt   time.Time `db:"created_at"`
}
