package main

import (
	"db_api/pkg/db"
	add_user_post "db_api/pkg/handlers/add_user_post"
	"log"
	"net/http"
)

func main() {
	database, err := db.NewDB()
	if err != nil {
		log.Fatalf("failed to initialize db: %v", err)
	}

	h := &add_user_post.Handler{DB: database}

	http.HandleFunc("/users", h.Handle)

	log.Println("Server listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
