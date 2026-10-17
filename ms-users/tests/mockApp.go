package tests

import (
	"ms-users/internal"
	"github.com/gorilla/mux"
)

func InitializeMock(db_uri string, db_name string, collection string) *internal.App {
	a := &internal.App{}
	a.Repository = NewMockRepository(db_uri, db_name, collection)
	a.Router = mux.NewRouter()
	a.InitializeRoutes()

	return a
}
