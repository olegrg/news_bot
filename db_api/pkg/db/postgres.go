package db

import (
	"fmt"
	"log"
	"os"

	sq "github.com/Masterminds/squirrel"
	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq"
)

type DB struct {
	Conn   *sqlx.DB
	SqlBld sq.StatementBuilderType
}

func NewDB() (*DB, error) {
	host := os.Getenv("POSTGRES_HOST")
	port := os.Getenv("POSTGRES_PORT")
	user := os.Getenv("POSTGRES_USER")
	password := os.Getenv("POSTGRES_PASSWORD")
	dbname := os.Getenv("POSTGRES_DB")

	dsn := fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		host, port, user, password, dbname,
	)

	conn, err := sqlx.Connect("postgres", dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to db: %w", err)
	}

	log.Println("Connected to PostgreSQL")

	builder := sq.StatementBuilder.PlaceholderFormat(sq.Dollar)

	return &DB{
		Conn:   conn,
		SqlBld: builder,
	}, nil
}
