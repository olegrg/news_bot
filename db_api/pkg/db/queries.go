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
		Columns("message_id", "grouped_id", "channel_id", "published_at", "content", "views", "reactions", "comments", "forwards", "score").
		Values(post.MessageID, post.GroupedID, post.ChannelID, post.PublishedAt, post.Content, post.Views, post.Reactions, post.Comments, post.Forwards, post.Score).
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

	db.UpdateChannelOffsetMessageID(ctx, post.ChannelID, post.MessageID)

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
		Suffix("ON CONFLICT (user_id, channel_id) DO UPDATE SET policy = COALESCE(subscriptions.policy, '{}'::jsonb) || EXCLUDED.policy").
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

func (db *DB) GetChannelIDByTelegramID(ctx context.Context, telegramID int64) (int64, error) {
	query, args, err := db.SqlBld.
		Select("id").
		From(channelTableName).
		Where(sq.Eq{"telegram_id": telegramID}).
		ToSql()
	if err != nil {
		return 0, fmt.Errorf("failed to build channel lookup query: %w", err)
	}

	var channelID int64
	if err := db.Conn.GetContext(ctx, &channelID, query, args...); err != nil {
		return 0, fmt.Errorf("failed to find channel: %w", err)
	}

	return channelID, nil
}

func (db *DB) GetPersonalizedTopPosts(ctx context.Context, userID int64) ([]models.ScoredPost, error) {
	subscriptionTable := "subscriptions"

	subQuery, subArgs, err := db.SqlBld.
		Select(
			fmt.Sprintf("%s.channel_id", subscriptionTable),
			fmt.Sprintf("%s.policy", subscriptionTable),
		).
		From(subscriptionTable).
		Where(sq.Eq{fmt.Sprintf("%s.user_id", subscriptionTable): userID}).
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
		_ = json.Unmarshal(sub.Policy, &policy)
		if policy.TopN <= 0 {
			policy.TopN = 1
		}
		maxAgeDays := 14

		sqlStr := `
WITH ranked AS (
    SELECT
        COALESCE(p.grouped_id, p.message_id) AS group_id,
        MAX(p.score) AS max_score
    FROM posts p
    LEFT JOIN user_seen_posts usp ON usp.post_id = p.id AND usp.user_id = $2
    WHERE p.channel_id = $1
      AND usp.post_id IS NULL
      AND p.published_at >= NOW() - ($4::text || ' days')::interval
    GROUP BY group_id
    ORDER BY max_score DESC
    LIMIT $3
)
SELECT
    COALESCE(c.link, '') AS link,
    c.telegram_id AS telegram_id,
    p.id AS post_id,
    COALESCE(p.grouped_id, p.message_id) AS group_id,
    p.message_id AS message_id
FROM posts p
JOIN channels c ON c.id = p.channel_id
JOIN ranked r ON r.group_id = COALESCE(p.grouped_id, p.message_id)
WHERE p.channel_id = $1
ORDER BY r.max_score DESC, p.message_id ASC`

		type rawRow struct {
			Link       string `db:"link"`
			TelegramID int64  `db:"telegram_id"`
			PostID     int64  `db:"post_id"`
			GroupID    int64  `db:"group_id"`
			MessageID  int64  `db:"message_id"`
		}
		var rows []rawRow
		if err := db.Conn.SelectContext(ctx, &rows, sqlStr, sub.ChannelID, userID, policy.TopN, maxAgeDays); err != nil {
			return nil, fmt.Errorf("failed to fetch posts for channel %d: %w", sub.ChannelID, err)
		}

		if len(rows) == 0 {
			continue
		}

		grouped := make(map[int64]*models.ScoredPost)
		groupOrder := make([]int64, 0)
		seenPostIDs := make([]int64, 0, len(rows))

		for _, row := range rows {
			seenPostIDs = append(seenPostIDs, row.PostID)
			entry, exists := grouped[row.GroupID]
			if !exists {
				grouped[row.GroupID] = &models.ScoredPost{
					Link:       row.Link,
					TelegramID: row.TelegramID,
					MessageIDs: []int64{row.MessageID},
				}
				groupOrder = append(groupOrder, row.GroupID)
				continue
			}
			entry.MessageIDs = append(entry.MessageIDs, row.MessageID)
		}

		if err := db.MarkPostsSeen(ctx, userID, seenPostIDs); err != nil {
			return nil, fmt.Errorf("failed to mark posts seen for user %d and channel %d: %w", userID, sub.ChannelID, err)
		}

		for _, groupID := range groupOrder {
			result = append(result, *grouped[groupID])
		}
	}

	return result, nil
}

func (db *DB) MarkPostsSeen(ctx context.Context, userID int64, postIDs []int64) error {
	if len(postIDs) == 0 {
		return nil
	}

	for _, postID := range postIDs {
		query, args, err := db.SqlBld.
			Insert("user_seen_posts").
			Columns("user_id", "post_id").
			Values(userID, postID).
			Suffix("ON CONFLICT (user_id, post_id) DO NOTHING").
			ToSql()
		if err != nil {
			return fmt.Errorf("failed to build seen insert query: %w", err)
		}
		if _, err := db.Conn.ExecContext(ctx, query, args...); err != nil {
			return fmt.Errorf("failed to insert seen post relation: %w", err)
		}
	}

	return nil
}

func (db *DB) UpdateChannelOffsetMessageID(ctx context.Context, channelID int64, telegramPostID int64) error {
	query, args, err := db.SqlBld.
		Update(channelTableName).
		Set("offset_message_id", telegramPostID).
		Where(sq.Eq{"id": channelID}).
		ToSql()
	if err != nil {
		return fmt.Errorf("failed to build update query: %w", err)
	}

	_, err = db.Conn.ExecContext(ctx, query, args...)
	if err != nil {
		return fmt.Errorf("failed to execute update query: %w", err)
	}

	return nil
}

func (db *DB) UpdateSubscriptionOffsetMessageID(ctx context.Context, userID, channelID, telegramPostID int64) error {
	query, args, err := db.SqlBld.
		Update("subscriptions").
		Set("offset_message_id", telegramPostID).
		Where(sq.Eq{
			"user_id":    userID,
			"channel_id": channelID,
		}).
		ToSql()
	if err != nil {
		return fmt.Errorf("failed to build update query: %w", err)
	}

	_, err = db.Conn.ExecContext(ctx, query, args...)
	if err != nil {
		return fmt.Errorf("failed to execute update query: %w", err)
	}

	return nil
}

func (db *DB) GetUserSubscriptionOffsets(ctx context.Context, userID int64) ([]models.ChannelOffset, error) {
	query := db.SqlBld.
		Select(
			fmt.Sprintf("%s.channel_id", subscriptionTableName),
			fmt.Sprintf("%s.telegram_id", channelTableName),
			fmt.Sprintf("%s.link", channelTableName),
			fmt.Sprintf("%s.offset_message_id", channelTableName),
		).
		From(subscriptionTableName).
		Join(fmt.Sprintf("%s ON %s.id = %s.channel_id", channelTableName, channelTableName, subscriptionTableName)).
		Where(sq.Eq{fmt.Sprintf("%s.user_id", subscriptionTableName): userID})

	sqlStr, args, err := query.ToSql()
	if err != nil {
		return nil, fmt.Errorf("failed to build subscription offsets query: %w", err)
	}

	var result []models.ChannelOffset
	if err := db.Conn.SelectContext(ctx, &result, sqlStr, args...); err != nil {
		return nil, fmt.Errorf("failed to fetch subscription offsets: %w", err)
	}

	return result, nil
}

func (db *DB) GetUserSubscriptions(ctx context.Context, userID int64) ([]models.SubscriptionInfo, error) {
	query := `
SELECT
    s.channel_id AS channel_id,
    c.telegram_id AS channel_telegram_id,
    c.title AS title,
    COALESCE(c.link, '') AS link,
    COALESCE(s.policy, '{}'::jsonb) AS policy
FROM subscriptions s
JOIN channels c ON c.id = s.channel_id
WHERE s.user_id = $1
ORDER BY c.title`

	var result []models.SubscriptionInfo
	if err := db.Conn.SelectContext(ctx, &result, query, userID); err != nil {
		return nil, fmt.Errorf("failed to fetch subscriptions: %w", err)
	}

	return result, nil
}

func (db *DB) DeleteSubscription(ctx context.Context, userID, channelID int64) error {
	query, args, err := db.SqlBld.
		Delete(subscriptionTableName).
		Where(sq.Eq{
			"user_id":    userID,
			"channel_id": channelID,
		}).
		ToSql()
	if err != nil {
		return fmt.Errorf("failed to build delete subscription query: %w", err)
	}

	_, err = db.Conn.ExecContext(ctx, query, args...)
	if err != nil {
		return fmt.Errorf("failed to execute delete subscription: %w", err)
	}

	return nil
}

func (db *DB) GetImmediateSubscriptions(ctx context.Context) ([]models.ImmediateSubscription, error) {
	query := `
SELECT
    u.telegram_id AS user_telegram_id,
    c.telegram_id AS channel_telegram_id,
    COALESCE(c.link, '') AS link
FROM subscriptions s
JOIN users u ON u.id = s.user_id
JOIN channels c ON c.id = s.channel_id
WHERE COALESCE(s.policy->>'send_immediately', 'false') = 'true'`

	var result []models.ImmediateSubscription
	if err := db.Conn.SelectContext(ctx, &result, query); err != nil {
		return nil, fmt.Errorf("failed to fetch immediate subscriptions: %w", err)
	}

	return result, nil
}
