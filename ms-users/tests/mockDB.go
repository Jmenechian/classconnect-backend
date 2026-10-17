package tests

import (
	"log"
	"ms-users/internal"
)

type mockUserService struct {
	userService *internal.UserService
}

func (repo *mockUserService) CreateCourse() int {
	return 0
}

func NewMockRepository(dbUri string, dbName string, collectionName string) internal.UserRepository {
	// Create client and connect to db server
	client, err := internal.InitializeDB(dbUri)
	if err != nil {
		log.Fatal(err)
	}
	collection := client.Database(dbName).Collection(collectionName)

	// Create auth service
	auth := mockTokenService{}
	emails := internal.NewMockEmailService()

	return &mockUserService{userService: internal.NewUserService(client, collection, &auth, emails)}
}

func (repo *mockUserService) InsertUser(u internal.User) (string, error) {
	return repo.userService.InsertUser(u)
}

func (repo *mockUserService) GetUsers() ([]internal.AppUser, error) {
	return repo.userService.GetUsers()
}

func (repo *mockUserService) GetUser(id string) (internal.AppUser, error) {
	return repo.userService.GetUser(id)
}

func (repo *mockUserService) GetAdmins() ([]internal.AppUser, error) {
	return repo.userService.GetAdmins()
}

func (repo *mockUserService) GetAdmin(id string) (internal.AppUser, error) {
	return repo.userService.GetAdmin(id)
}

func (repo *mockUserService) UpdateToken(uid string, token string, notifToken string) (int, error) {
	return repo.userService.UpdateToken(uid, token, notifToken)
}

func (repo *mockUserService) DeleteUser(id string) error {
	return repo.userService.DeleteUser(id)
}

func (repo *mockUserService) UpdateUserDB(u internal.UserUpdate, id string) error {
	return repo.userService.UpdateUserDB(u, id)
}

func (repo *mockUserService) MuteUnmuteUser(mute bool, id string) error {
	return repo.userService.MuteUnmuteUser(mute, id)
}

func (repo *mockUserService) GetUserByUID(uid string) (internal.User, error) {
	return repo.userService.GetUserByUID(uid)
}

func (repo *mockUserService) GetUsersByEmailPrefix(prefix string) ([]internal.AppUser, error) {
	return repo.userService.GetUsersByEmailPrefix(prefix)
}

func (repo *mockUserService) SendNotification(notif internal.Notification) error {
	return repo.userService.SendNotification(notif) 
}

func (repo *mockUserService) Verify(token string) (internal.UserVerification, error) {
	return repo.userService.Verify(token) 
}

