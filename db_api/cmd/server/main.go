package main

import (
	"db_api/pkg/db"
	add_post_post "db_api/pkg/handlers/add_post_post"
	add_subscription_post "db_api/pkg/handlers/add_subscription_post"
	add_user_post "db_api/pkg/handlers/add_user_post"
	get_offsets_get "db_api/pkg/handlers/get_channels_offset_by_user_get"
	get_posts_get "db_api/pkg/handlers/get_posts_get"
	"log"
	"net/http"
)

func main() {
	database, err := db.NewDB()
	if err != nil {
		log.Fatalf("failed to initialize db: %v", err)
	}

	userHandler := &add_user_post.Handler{DB: database}
	postHandler := &add_post_post.Handler{DB: database}
	subscribeHandler := &add_subscription_post.Handler{DB: database}
	topPostsHandler := &get_posts_get.Handler{DB: database}
	offsetsHandler := &get_offsets_get.Handler{DB: database}

	http.HandleFunc("/users", userHandler.Handle)
	http.HandleFunc("/posts", postHandler.Handle)
	http.HandleFunc("/subscribe", subscribeHandler.Handle)
	http.HandleFunc("/top-posts", topPostsHandler.Handle)
	http.HandleFunc("/offsets", offsetsHandler.Handle)

	log.Println("Server listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
