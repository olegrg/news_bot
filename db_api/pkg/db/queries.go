package db

import (
	"context"
	"database/sql"
	"db_api/pkg/models"
	"encoding/json"
	"fmt"

	sq "github.com/Masterminds/squirrel"
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

func (db *DB) AddPost(ctx context.Context, post *models.Post) (int64, error) {
	query, args, err := db.SqlBld.
		Insert("posts").
		Columns("message_id", "channel_id", "published_at", "content", "views", "forwards", "score").
		Values(post.MessageID, post.ChannelID, post.PublishedAt, post.Content, post.Views, post.Forwards, post.Score).
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

func (db *DB) AddChannel(ctx context.Context, channel *models.Channel) (int64, error) {
	query, args, err := db.SqlBld.
		Insert(channelTableName).
		Columns("telegram_id", "link", "title", "is_private").
		Values(channel.TelegramID, channel.Link, channel.Title, channel.IsPrivate).
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

func (db *DB) AddSubscription(ctx context.Context, sub *models.Subscription) error {
	var policyJSON interface{} = nil
	var err error

	if sub.Policy != nil {
		data, err := json.Marshal(sub.Policy)
		if err != nil {
			return fmt.Errorf("failed to marshal policy: %w", err)
		}
		policyJSON = data
	}

	if policyJSON == nil {
		policyJSON = "{}"
	}

	query, args, err := db.SqlBld.
		Insert(subscriptionTableName).
		Columns("user_id", "channel_id", "policy").
		Values(sub.UserID, sub.ChannelID, policyJSON).
		Suffix("ON CONFLICT (user_id, channel_id) DO UPDATE SET policy = EXCLUDED.policy").
		ToSql()
	if err != nil {
		return fmt.Errorf("failed to build insert query: %w", err)
	}

	_, err = db.Conn.ExecContext(ctx, query, args...)
	if err != nil {
		return fmt.Errorf("failed to execute insert query: %w", err)
	}

	return nil
}

func (db *DB) GetOrCreateChannel(ctx context.Context, channel *models.Channel) (int64, error) {
	query, args, err := db.SqlBld.
		Select("id").
		From(channelTableName).
		Where(sq.Eq{"telegram_id": channel.TelegramID}).
		ToSql()
	if err != nil {
		return 0, fmt.Errorf("failed to build select query: %w", err)
	}

	var existingID int64
	err = db.Conn.GetContext(ctx, &existingID, query, args...)
	if err == nil {
		return existingID, nil
	}

	if err != sql.ErrNoRows {
		return 0, fmt.Errorf("failed to query channel: %w", err)
	}

	return db.AddChannel(ctx, channel)
}

func (db *DB) GetOrCreateSubscription(ctx context.Context, sub *models.Subscription) (created bool, err error) {
	query, args, err := db.SqlBld.
		Select("1").
		From(subscriptionTableName).
		Where(sq.Eq{
			"user_id":    sub.UserID,
			"channel_id": sub.ChannelID,
		}).
		ToSql()
	if err != nil {
		return false, fmt.Errorf("failed to build select query: %w", err)
	}

	var dummy int
	err = db.Conn.GetContext(ctx, &dummy, query, args...)
	if err == nil {
		return false, nil
	}
	if err != sql.ErrNoRows {
		return false, fmt.Errorf("failed to query subscription: %w", err)
	}

	err = db.AddSubscription(ctx, sub)
	if err != nil {
		return false, fmt.Errorf("failed to insert subscription: %w", err)
	}

	return true, nil
}

func (db *DB) GetOrCreateUser(ctx context.Context, user *models.User) (int64, error) {
	query, args, err := db.SqlBld.
		Select("id").
		From(userTableName).
		Where(sq.Eq{"telegram_id": user.TelegramID}).
		ToSql()
	if err != nil {
		return 0, fmt.Errorf("failed to build select query: %w", err)
	}

	var existingID int64
	err = db.Conn.GetContext(ctx, &existingID, query, args...)
	if err == nil {
		return existingID, nil
	}
	if err != sql.ErrNoRows {
		return 0, fmt.Errorf("failed to query user: %w", err)
	}

	return db.AddUser(ctx, user)
}

func (db *DB) GetOrCreatePost(ctx context.Context, post *models.Post) (int64, error) {
	query, args, err := db.SqlBld.
		Select("id").
		From(postTableName).
		Where(sq.Eq{
			"message_id": post.MessageID,
			"channel_id": post.ChannelID,
		}).
		ToSql()
	if err != nil {
		return 0, fmt.Errorf("failed to build select query: %w", err)
	}

	var existingID int64
	err = db.Conn.GetContext(ctx, &existingID, query, args...)
	if err == nil {
		return existingID, nil
	}
	if err != sql.ErrNoRows {
		return 0, fmt.Errorf("failed to query post: %w", err)
	}

	return db.AddPost(ctx, post)
}

func (db *DB) GetUserIDByTelegramID(ctx context.Context, telegramID int64) (int64, error) {
	query, args, err := db.SqlBld.
		Select("id").
		From("users").
		Where(sq.Eq{"telegram_id": telegramID}).
		ToSql()
	if err != nil {
		return 0, fmt.Errorf("failed to build user lookup query: %w", err)
	}

	var userID int64
	err = db.Conn.GetContext(ctx, &userID, query, args...)
	if err != nil {
		return 0, fmt.Errorf("failed to find user: %w", err)
	}

	return userID, nil
}

func (db *DB) GetPersonalizedTopPosts(ctx context.Context, userID int64) ([]models.ScoredPost, error) {
	subQuery, subArgs, err := db.SqlBld.
		Select("channel_id", "policy").
		From("subscriptions").
		Where(sq.Eq{"user_id": userID}).
		ToSql()
	if err != nil {
		return nil, fmt.Errorf("failed to build subscriptions query: %w", err)
	}

	type subRow struct {
		ChannelID int64           `db:"channel_id"`
		Policy    json.RawMessage `db:"policy"`
	}

	var subs []subRow
	if err := db.Conn.SelectContext(ctx, &subs, subQuery, subArgs...); err != nil {
		return nil, fmt.Errorf("failed to fetch subscriptions: %w", err)
	}

	var result []models.ScoredPost

	for _, sub := range subs {
		var policy struct {
			TopN int `json:"top_n"`
		}
		policy.TopN = 1
		_ = json.Unmarshal(sub.Policy, &policy)

		queryBuilder := db.SqlBld.
			Select("channels.telegram_id AS channel_id", "posts.message_id").
			From("posts").
			Join("channels ON channels.id = posts.channel_id").
			Where(sq.Eq{"posts.channel_id": sub.ChannelID}).
			OrderBy("posts.score DESC").
			Limit(uint64(policy.TopN))

		postQuery, postArgs, err := queryBuilder.ToSql()
		if err != nil {
			return nil, fmt.Errorf("failed to build posts query: %w", err)
		}

		var posts []models.ScoredPost
		if err := db.Conn.SelectContext(ctx, &posts, postQuery, postArgs...); err != nil {
			return nil, fmt.Errorf("failed to fetch posts for channel %d: %w", sub.ChannelID, err)
		}

		result = append(result, posts...)
	}

	return result, nil
}
