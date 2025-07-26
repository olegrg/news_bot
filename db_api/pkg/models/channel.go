package models

import "time"

type Channel struct {
	ID         int64     `db:"id" json:"id"`
	TelegramID int64     `db:"telegram_id" json:"telegram_id"`
	Link       string    `db:"link" json:"link"`
	Title      string    `db:"title" json:"title"`
	IsPrivate  bool      `db:"is_private" json:"is_private"`
	CreatedAt  time.Time `db:"created_at" json:"created_at"`
}
