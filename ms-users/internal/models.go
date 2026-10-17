package internal


type Response struct {
	Data User `json:"data"`
}
type ErrorResponse struct {
	Status int `json:"status"`
	Title string `json:"title"`
	Description string `json:"description"`
}

type User struct {
	Id			string `json:"id" bson:"_id,omitempty"`		// Id en esta bd
	UID     	string `json:"uid"`							// Id en firebase 
	Token 		string `json:"token"`						// Auth token
	NotifToken 	string `json:"notifToken"`				// Notif token
	Name 		*string `json:"name"`						// Profile info
	Surname 	*string `json:"surname"`  					
	Email   	string  `json:"email"`
	Country 	*string `json:"country"` 
	IsAdmin 	bool `json:"isAdmin"`	
	MuteNotif	bool `json:"muteNotif"`					  
}

type AppUser struct {
	Id		string `json:"id" bson:"_id,omitempty"`		// Id en esta bd
	UID     string `json:"uid"`							// Id en firebase 
	Name 	*string `json:"name"`						// Profile info
	Surname *string `json:"surname"`  					
	Email   string  `json:"email"`
	Country *string `json:"country"` 
	MuteNotif	bool `json:"muteNotif"`					  
}

type UserUpdate struct {
	UID     string `json:"uid"`							// Id en firebase 
	Token 	string `json:"token"`						// Auth token
	NotifToken 	string `json:"notifToken"`				// Notif token
	Name 	*string `json:"name"`						// Profile info
	Surname *string `json:"surname"`  					
	Country *string `json:"country"` 	
}

type UserVerification struct {
	Id			string `json:"id" bson:"_id,omitempty"`		// Id en esta bd
	IsAdmin 	bool `json:"isAdmin"`	
}

func (u User) validate() bool {
	return u.UID != "" && u.Token != "" && u.Email != "" && u.NotifToken != ""
}

func (u UserUpdate) validate() bool {
	return u.UID != "" 
}

type Notification struct {
	TemplateId int64
	Title string
	Message string
	Users []string
	Metadata map[string]string
}