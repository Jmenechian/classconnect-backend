package main

import (
	"ms-users/tests"
	"fmt"
	"os"
)

func main() {
	db_uri := fmt.Sprintf("mongodb://%s:%s@%s:%s/%s?authSource=admin",
		os.Getenv("MONGO_USER"),
		os.Getenv("MONGO_PASSWORD"),
		os.Getenv("DATABASE_HOST"),
		os.Getenv("DATABASE_PORT"),
		os.Getenv("MONGO_DB"),
	)	

	app := tests.InitializeMock(db_uri, os.Getenv("MONGO_DB"), os.Getenv("MONGO_COLLECTION") )
	app.Run(os.Getenv("HOST"), os.Getenv("PORT"))
}
