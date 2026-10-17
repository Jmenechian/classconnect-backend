package internal

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/gorilla/mux"
	ddtracer "gopkg.in/DataDog/dd-trace-go.v1/ddtrace/tracer"
	httptrace "gopkg.in/DataDog/dd-trace-go.v1/contrib/net/http"
)

type App struct {
	Router     *mux.Router
	Repository UserRepository
}

func Initialize(db_uri string, db_name string, collection string) *App {
	a := &App{}
	a.Repository = NewRepository(db_uri, db_name, collection)
	a.Router = mux.NewRouter()
	a.InitializeRoutes()

	return a
}

func (a *App) Run(host string, port string) {
	serverAddr := fmt.Sprintf("%s:%s",
		host,
		port,
	)
	fmt.Println("Starting server on 0.0.0.0")
	log.Fatal(http.ListenAndServe(serverAddr, a.Router))
}

func (a *App) InitializeRoutes() {
	// Add tracing middleware
	a.Router.Use(func(next http.Handler) http.Handler {
		return httptrace.WrapHandler(next, "ms-users", "gorilla/mux")
	})
	a.Router.Use(headers)
	
	a.Router.HandleFunc("/auth/signup", a.SignUpUser).Methods("POST")
	a.Router.HandleFunc("/auth/signin", a.SignInUser).Methods("POST")
	a.Router.HandleFunc("/auth/admin/signup", a.SignUpAdmin).Methods("POST")
	a.Router.HandleFunc("/auth/admin/signin", a.SignInAdmin).Methods("POST")
	a.Router.HandleFunc("/auth/verify", a.Verify).Methods("GET")

	a.Router.HandleFunc("/users", a.GetUsers).Methods("GET")
	a.Router.HandleFunc("/users/search", a.SearchUsersByEmail).Methods("GET")
	a.Router.HandleFunc("/users/{id}", a.GetUser).Methods("GET")
	a.Router.HandleFunc("/admins", a.GetAdmins).Methods("GET")
	a.Router.HandleFunc("/admins/{id}", a.GetAdmin).Methods("GET")

	a.Router.HandleFunc("/users/{id}", a.DeleteUser).Methods("DELETE")
	a.Router.HandleFunc("/users/{id}", a.UpdateUser).Methods("PUT")

	a.Router.HandleFunc("/notifications", a.PushNotifFirebase).Methods("POST")
	a.Router.HandleFunc("/notifications/{id}/mute", a.MuteUser).Methods("PUT")
	a.Router.HandleFunc("/notifications/{id}/unmute", a.UnmuteUser).Methods("PUT")

	a.Router.Methods("OPTIONS").HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
}

func (a *App) internalServerError(writer http.ResponseWriter) {
	writer.WriteHeader(500)
	errResponse := ErrorResponse{
		Status:      500,
		Title:       "Internal server error",
		Description: "The server was unable to complete your request",
	}
	if err := json.NewEncoder(writer).Encode(errResponse); err != nil {
		log.Println("Error encoding response:", err)
	}
}

func (a *App) clientError(writer http.ResponseWriter, http_code int, title string, description string) {
	writer.WriteHeader(http_code)
	errResponse := ErrorResponse{
		Status:      http_code,
		Title:       title,
		Description: description,
	}
	if err := json.NewEncoder(writer).Encode(errResponse); err != nil {
		log.Println("Error encoding response:", err)
	}
}

func headers(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		
		// Handle preflight requests (for CORS POST using localhost)
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusOK)
			return
		}

		// Add trace ID to response headers
		if span, ok := ddtracer.SpanFromContext(r.Context()); ok {
			w.Header().Set("X-Datadog-Trace-ID", fmt.Sprintf("%d", span.Context().TraceID()))
		}
		
		next.ServeHTTP(w, r)
	})
}

/*--------------------------------------------------------------------------------------------------------------------------*/
// User ABM functions
/*--------------------------------------------------------------------------------------------------------------------------*/

func (a *App) insertUser(u User) (string, error) {
	return a.Repository.InsertUser(u)
}

func (a *App) getUsers() ([]AppUser, error) {
	return a.Repository.GetUsers()
}

func (a *App) getUser(id string) (AppUser, error) {
	return a.Repository.GetUser(id)
}

func (a *App) getUserByUID(uid string) (User, error) {
	return a.Repository.GetUserByUID(uid)
}

func (a *App) deleteUser(id string) error {
	return a.Repository.DeleteUser(id)
}

func (a *App) updateToken(uid string, token string, notifToken string) (int, error) {
	return a.Repository.UpdateToken(uid, token, notifToken)
}

func (a *App) updateUser(u UserUpdate, id string) error {
	return a.Repository.UpdateUserDB(u, id)
}

func (a *App) muteUnmuteUserDB(mute bool, id string) error {
	return a.Repository.MuteUnmuteUser(mute, id)
}

func (a *App) getAdmins() ([]AppUser, error) {
	return a.Repository.GetAdmins()
}

func (a *App) getAdmin(id string) (AppUser, error) {
	return a.Repository.GetAdmin(id)
}

func (a *App) verify(token string) (UserVerification, error) {
	return a.Repository.Verify(token)
}

/*--------------------------------------------------------------------------------------------------------------------------*/
// API functions
/*--------------------------------------------------------------------------------------------------------------------------*/

func (a *App) PushNotifFirebase(writer http.ResponseWriter, request *http.Request) {
	fmt.Println("Received HTTP POST PushNotification")
	if request.Method == http.MethodPost {
		var notif Notification
		err := json.NewDecoder(request.Body).Decode(&notif)
		if err != nil {
			a.internalServerError(writer)
			log.Println("Decodification error")
			fmt.Println(err.Error())
			return
		} else if err = a.Repository.SendNotification(notif); err != nil {
			a.internalServerError(writer)
			log.Println("Error sending notification")
			fmt.Println(err.Error())
			return
		} else {
			writer.WriteHeader(201)
			if err := json.NewEncoder(writer).Encode(map[string]Notification{"data": notif}); err != nil {
				log.Println("Error encoding response:", err)
			}
		}
	}
}

func (a *App) SignUpUser(writer http.ResponseWriter, request *http.Request) {
	a.SignUp(writer,request,false)
}

func (a *App) SignInUser(writer http.ResponseWriter, request *http.Request) {
	a.SignIn(writer,request,false)
}

func (a *App) SignUpAdmin(writer http.ResponseWriter, request *http.Request) {
	a.SignUp(writer,request,true)
}

func (a *App) SignInAdmin(writer http.ResponseWriter, request *http.Request) {
	a.SignIn(writer,request,true)
}

func (a *App) SignUp(writer http.ResponseWriter, request *http.Request, IsAdmin bool ) {
	fmt.Println("Received request for sign up user")
	if request.Method == http.MethodPost {
		// Set user info
		var u User
		err := json.NewDecoder(request.Body).Decode(&u)

		u.IsAdmin = IsAdmin
		if err != nil {
			a.internalServerError(writer)
			fmt.Println(err.Error())
			return
		}
		if !u.validate() {
			a.clientError(writer, 400, "No se indicó la información adecuada.", "Información faltante en la solicitud.")
			return
		}

		// Insert
		id, err := a.insertUser(u)
		if err != nil {
			if id == "HTTP401" {
				a.clientError(writer, 401, "Token de autenticación inválido", "Token de autenticación inválido.")
			} else {
				a.internalServerError(writer)
			}
			fmt.Println(err.Error())
			return
		}

		// Return result
		user, err := a.getUserByUID(u.UID)
		if err != nil {
			log.Println("Error retrieving signed up user:", err)
			a.clientError(writer,404,"User not found", "No se encontró el usuario especificado.")
			return
		}
		writer.WriteHeader(201)
		if err := json.NewEncoder(writer).Encode(map[string]User{"data": user}); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}

func (a *App) SignIn(writer http.ResponseWriter, request *http.Request, IsAdmin bool) {
	fmt.Println("Received request for sign in user")
	if request.Method == http.MethodPost {
		var u User
		err := json.NewDecoder(request.Body).Decode(&u)

		u.IsAdmin = IsAdmin
		if err != nil {
			a.internalServerError(writer)
			fmt.Println(err.Error())
			return
		}

		user, err := a.getUserByUID(u.UID)
		if err != nil {
			log.Println("Error retrieving user:", err)
			a.clientError(writer,404,"User not found", "No se encontró el usuario especificado.")
			return
		} else if user.IsAdmin != IsAdmin {
			if IsAdmin {
				log.Println("Error Admin intenta loguearse como user:  ", user.UID, user.Email )
				a.clientError(writer,404,"SignIn client Error", "Error admin intenta loguearse como user")
				return
			} else {
				log.Println("Error User intenta loguearse como admin:  ", user.UID, user.Email )
				a.clientError(writer,404,"SignIn client Error", "Error user intenta loguearse como admin")
				return
			}
		}

		code, err := a.updateToken(u.UID, u.Token, u.NotifToken)
		if err != nil {
			if code == 401 {
				a.clientError(writer, 401, "Token de autenticación inválido", "Token de autenticación inválido.")
			} else {
				a.internalServerError(writer)
			}

			fmt.Println(err.Error())
			return
		}

		user.Token = u.Token
		writer.WriteHeader(200)
		if err := json.NewEncoder(writer).Encode(map[string]User{"data": user}); err != nil {
			log.Println("Error encoding response:", err)
		}

	}
}

func (a *App) Verify(writer http.ResponseWriter, request *http.Request) {
	log.Println("Veryfing user token")
	if request.Method == http.MethodGet {
		token := request.Header.Get("Token")
		if token == "" {
			log.Println("APP: CLIENTE NO ENVIO TOKEN")
			a.clientError(writer, 401, "No autorizado. Token inválido", "No autorizado. Token inválido")
			return
		} 
		result, err := a.verify(token)
		if err != nil {
			log.Println("APP: TOKEN RECHAZADO")
			a.clientError(writer, 401, "No autorizado. Token inválido", "No autorizado. Token inválido")
			return
		}
		writer.WriteHeader(200)
		log.Println("APP: TOKEN VERIFICADO OK")
		if err = json.NewEncoder(writer).Encode(map[string]UserVerification{"data": result}); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
	
}

func (a *App) GetUsers(writer http.ResponseWriter, request *http.Request) {
	log.Println("Requesting users")
	if request.Method == http.MethodGet {
		users, err := a.getUsers()
		if err != nil {
			a.internalServerError(writer)
			fmt.Println(err.Error())
			return
		}
		writer.WriteHeader(200)
		log.Println("Returning users")
		if err := json.NewEncoder(writer).Encode(map[string]interface{}{"data": users}); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}

func (a *App) GetUser(writer http.ResponseWriter, request *http.Request) {
	log.Println("Requesting user")
	if request.Method == http.MethodGet {
		userId := mux.Vars(request)["id"]
		user, err := a.getUser(userId)
		if err != nil {
			a.clientError(writer, 404, "User not found", "No se encontró el usuario especificado.")
			return
		}
		writer.WriteHeader(200)
		log.Println("Returning user successfully")
		if err := json.NewEncoder(writer).Encode(map[string]AppUser{"data": user}); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}

func (a *App) GetAdmins(writer http.ResponseWriter, request *http.Request) {
	log.Println("Requesting admins")
	if request.Method == http.MethodGet {
		users, err := a.getAdmins()
		if err != nil {
			a.internalServerError(writer)
			fmt.Println(err.Error())
			return
		}
		writer.WriteHeader(200)
		log.Println("Returning admins")
		if err := json.NewEncoder(writer).Encode(map[string]interface{}{"data": users}); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}

func (a *App) GetAdmin(writer http.ResponseWriter, request *http.Request) {
	log.Println("Requesting admin")
	if request.Method == http.MethodGet {
		userId := mux.Vars(request)["id"]
		user, err := a.getAdmin(userId)
		if err != nil {
			a.clientError(writer, 404, "User not found", "No se encontró el usuario especificado.")
			return
		}
		writer.WriteHeader(200)
		log.Println("Returning admin successfully")
		if err := json.NewEncoder(writer).Encode(map[string]AppUser{"data": user}); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}

func (a *App) DeleteUser(writer http.ResponseWriter, request *http.Request) {
	if request.Method == http.MethodDelete {
		userId := mux.Vars(request)["id"]
		err := a.deleteUser(userId)

		if err != nil {
			a.clientError(writer, 404, "User not found", "No se encontró el usuario especificado.")
			return
		}
		writer.WriteHeader(204)
		if err := json.NewEncoder(writer).Encode("User deleted succesfully"); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}

func (a *App) UpdateUser(writer http.ResponseWriter, request *http.Request) {
	if request.Method == http.MethodPut {
		var u UserUpdate
		userId := mux.Vars(request)["id"]
		err := json.NewDecoder(request.Body).Decode(&u)

		if err != nil {
			a.internalServerError(writer)
			fmt.Println(err.Error())
			return
		}

		if !u.validate() {
			a.clientError(writer, 400, "No se indicó la información adecuada.", "Información faltante en la solicitud.")
			return
		}
		err = a.updateUser(u, userId)
		if err != nil {
			log.Printf("Error updating user: %v", err)
			a.clientError(writer, 404, "User not found", "No se encontró el usuario especificado.") //cambiar esto, aveces no es 404
			return
		}
		writer.WriteHeader(200)
		if err := json.NewEncoder(writer).Encode("User updated succesfully"); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}

func (a *App) muteUnmuteUser(writer http.ResponseWriter, request *http.Request, mute bool) {
	if request.Method == http.MethodPut {
		userId := mux.Vars(request)["id"]

		err := a.muteUnmuteUserDB(mute, userId)
		if err != nil {
			log.Printf("Error switching mute status for user: %v", err)
			a.clientError(writer, 404, "User not found", "No se encontró el usuario especificado.") //cambiar esto, aveces no es 404
			return
		}
		writer.WriteHeader(200)		
		if err := json.NewEncoder(writer).Encode(a.returnMessageMute(mute)); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}

func (a *App) UnmuteUser(writer http.ResponseWriter, request *http.Request) {
	a.muteUnmuteUser(writer,request,false)
}
func (a *App) MuteUser(writer http.ResponseWriter, request *http.Request) {
	a.muteUnmuteUser(writer,request,true)
}

func (a *App) returnMessageMute(mute bool) string {
	if mute {
		return "Successfully muted user notifications"
	} else {
		return "Successfully unmuted user notifications"
	}
}

func (a *App) SearchUsersByEmail(writer http.ResponseWriter, request *http.Request) {
	log.Println("Searching users by email prefix")
	if request.Method == http.MethodGet {
		prefix := request.URL.Query().Get("prefix")
		if prefix == "" {
			a.clientError(writer, 400, "Missing prefix parameter", "The 'prefix' query parameter is required")
			return
		}

		users, err := a.Repository.GetUsersByEmailPrefix(prefix)
		if err != nil {
			a.internalServerError(writer)
			fmt.Println(err.Error())
			return
		}

		writer.WriteHeader(200)
		log.Println("Returning users by email prefix")
		if err := json.NewEncoder(writer).Encode(map[string]interface{}{"data": users}); err != nil {
			log.Println("Error encoding response:", err)
		}
	}
}
