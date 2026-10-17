package main

import (
	"ms-users/internal"
	"fmt"
	"os"
	"gopkg.in/DataDog/dd-trace-go.v1/ddtrace/tracer"
)

func main() {
	// Start the tracer
	tracer.Start(
		tracer.WithService("ms-users"),
		tracer.WithEnv(os.Getenv("ENVIRONMENT")),
	)
	defer tracer.Stop()

	var uri string
	env := os.Getenv("ENVIRONMENT")
	if env == "production" {
		uri = os.Getenv("MONGO_URI")
	} else {
		uri = fmt.Sprintf("mongodb://%s:%s@%s:%s/%s?authSource=admin",
			os.Getenv("MONGO_USER"),
			os.Getenv("MONGO_PASSWORD"),
			os.Getenv("DATABASE_HOST"),
			os.Getenv("DATABASE_PORT"),
			os.Getenv("MONGO_DB"),
		)	
	}

	app := internal.Initialize(uri, os.Getenv("MONGO_DB"), os.Getenv("MONGO_COLLECTION") )

	if env == "production" {
		go internal.ConsumeNotifications(app)
	}

	app.Run(os.Getenv("HOST"), os.Getenv("PORT"))
}
