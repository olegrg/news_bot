package models

import "time"

type User struct {
	ID         int64     `db:"id" json:"id"`
	Username   string    `db:"username" json:"username"`
	FirstName  string    `db:"first_name" json:"first_name"`
	LastName   string    `db:"last_name" json:"last_name"`
	TelegramID int64     `db:"telegram_id" json:"telegram_id"`
	CreatedAt  time.Time `db:"created_at" json:"created_at"`
}
