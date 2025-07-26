package db

import (
	"context"
	"db_api/pkg/models"
	"fmt"
)

func (db *DB) AddUser(ctx context.Context, user *models.User) (int64, error) {
	query, args, err := db.SqlBld.
		Insert(userTableName).
		Columns("username", "first_name", "last_name", "telegram_id").
		Values(user.Username, user.FirstName, user.LastName, user.TelegramID).
		Suffix("RETURNING id").
		ToSql()
	if err != nil {
		return 0, fmt.Errorf("failed to build insert query: %w", err)
	}

	var id int64
	err = db.Conn.QueryRowContext(ctx, query, args...).Scan(&id)
	if err != nil {
		return 0, fmt.Errorf("failed to execute insert query: %w", err)
	}

	return id, nil
}
