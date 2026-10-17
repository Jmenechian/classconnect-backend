package internal

import (
	"context"
	"fmt"
	"log"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type UserRepository interface {
	InsertUser(u User) (string, error)
	GetUsers() ([]AppUser, error)
	GetUser(id string) (AppUser, error)
	GetAdmins() ([]AppUser, error)
	GetAdmin(id string) (AppUser, error)
	GetUserByUID(uid string) (User, error)
	DeleteUser(id string) error
	UpdateToken(uid string, token string, notifToken string) (int, error)
	UpdateUserDB(u UserUpdate, id string) error
	MuteUnmuteUser(mute bool, id string) error
	GetUsersByEmailPrefix(prefix string) ([]AppUser, error)
	SendNotification(notif Notification) error
	Verify(token string) (UserVerification, error)
}

type UserService struct {
	client     *mongo.Client
	collection *mongo.Collection
	auth       tokenVerifier
	email	   emailSender	
}

func (*UserService) CreateCourse() int {
	return 0
}

func NewUserService(client *mongo.Client, collection *mongo.Collection, auth tokenVerifier, email emailSender) *UserService {
	return &UserService{client: client, collection: collection, auth: auth, email: email}
}

func NewRepository(dbUri string, dbName string, collectionName string) UserRepository {
	// Create client and connect to db server
	client, err := InitializeDB(dbUri)
	if err != nil {
		log.Fatal(err)
	}
	collection := client.Database(dbName).Collection(collectionName)

	// Create auth service
	auth := NewTokenService()
	email := NewEmailService()

	return &UserService{client: client, collection: collection, auth: auth, email: email}
}

func InitializeDB(dbUri string) (*mongo.Client, error) {
	clientOpts := options.Client().ApplyURI(dbUri)
	client, err := mongo.Connect(context.TODO(), clientOpts)
	if err != nil {
		return client, err
	}
	err = client.Ping(context.TODO(), nil)
	if err != nil {
		return client, err
	}
	return client, nil
}

func (repo *UserService) InsertUser(u User) (string, error) {
	// Upsert User. If token or email or UID exist, it updates it. Else, it inserts it
	isTokenValid, err := repo.auth.VerifyToken(u.Token)

	if err != nil || !isTokenValid {
		return "HTTP401", err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

/*
	result, err := repo.collection.InsertOne(ctx, repo.format(u))
	if err != nil {
		return "", err
	}
	id := result.InsertedID.(primitive.ObjectID).Hex()
	return id, nil
*/

	filter := bson.M{
		"$or": []bson.M{
			{"uid": u.UID},
			{"email": u.Email},
		},
	}

	update := bson.M{
		"$set": buildUpdateData(u),
	}

	opts := options.Update().SetUpsert(true)

	result, err := repo.collection.UpdateOne(ctx, filter, update, opts)
	if err != nil {
		return "", err
	}

	if result.UpsertedID != nil {
		return result.UpsertedID.(primitive.ObjectID).Hex(), nil
	}

	var persisted User
	err = repo.collection.FindOne(ctx, filter).Decode(&persisted)
	if err != nil {
		return "", err
	}

	return persisted.Id, nil
}

func (repo *UserService) GetUsers() ([]AppUser, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	filter := bson.M{}
	cursor, err := repo.collection.Find(ctx, filter)
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := cursor.Close(ctx); err != nil {
			log.Println("Failed to close cursor:", err)
		}
	}()

	var users []AppUser
	for cursor.Next(ctx) {
		var u AppUser
		if err := cursor.Decode(&u); err != nil {
			log.Println("Failed to decode cursor result:", err)
		}
		users = append(users, u)
	}
	return users, nil
}

func (repo *UserService) GetUser(id string) (AppUser, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	objID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		return AppUser{}, err
	}
	var user AppUser
	filter := bson.M{"_id": objID,}

	err = repo.collection.FindOne(ctx, filter).Decode(&user)
	return user, err
}

func (repo *UserService) GetAdmins() ([]AppUser, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	filter := bson.M{	
		"IsAdmin": true,
	}
	cursor, err := repo.collection.Find(ctx, filter)
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := cursor.Close(ctx); err != nil {
			log.Println("Failed to close cursor:", err)
		}
	}()

	var users []AppUser
	for cursor.Next(ctx) {
		var u AppUser
		if err := cursor.Decode(&u); err != nil {
			log.Println("Failed to decode cursor result:", err)
		}
		users = append(users, u)
	}
	return users, nil
}

func (repo *UserService) GetAdmin(id string) (AppUser, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	objID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		return AppUser{}, err
	}
	var user AppUser
	filter := bson.M{	// Filter by _id and not admin users
		"_id": objID,
		"IsAdmin": true,
	}

	err = repo.collection.FindOne(ctx, filter).Decode(&user)
	return user, err
}

func (repo *UserService) GetUserByUID(uid string) (User, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	var user User
	filter := bson.M{	
		"uid": uid,
	}

	err := repo.collection.FindOne(ctx, filter).Decode(&user)
	return user, err
}

func (repo *UserService) Verify(token string) (UserVerification, error) {
	isTokenValid, err := repo.auth.VerifyToken(token)
	if err != nil || !isTokenValid {
		log.Println("Repository: TOKEN RECHAZADO POR FIREBASE")
		return UserVerification{}, err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	var user UserVerification
	err = repo.collection.FindOne(ctx, bson.M{"token": token}).Decode(&user)
	if err != nil {
		log.Println("Repository: TOKEN NO ENCONTRADO o ERROR CON LA BD")
		return UserVerification{}, err
	} else {
		return user, nil
	}
}


func (repo *UserService) UpdateToken(uid string, token string, notifToken string) (int, error) {
	isTokenValid, err := repo.auth.VerifyToken(token)
	if err != nil || !isTokenValid {
		return 401, err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	filter := bson.M{"uid": uid}
	update := bson.M{"$set": bson.M{"token": token, "notifToken": notifToken}}
	_, err = repo.collection.UpdateOne(ctx, filter, update)
	if err != nil {
		return 500, err
	} else {
		return 200, nil
	}
}

func (repo *UserService) DeleteUser(id string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	objID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		return err
	}
	_, err = repo.collection.DeleteOne(ctx, bson.M{"_id": objID})
	return err
}

func (repo *UserService) UpdateUserDB(u UserUpdate, id string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second) //si no lo encuentra error
	defer cancel()
	objID, err := primitive.ObjectIDFromHex(id)

	if err != nil {
		return err
	}

	var user User
	err = repo.collection.FindOne(ctx, bson.M{"_id": objID}).Decode(&user)
	if err != nil {
		return err
	}
/*
	if user.UID != u.UID || user.Token != u.Token {
		return fmt.Errorf("UID or token do not match")
	}
*/
	update := bson.M{}
	if u.Name != nil {
		update["name"] = *u.Name
	}
	if u.Surname != nil {
		update["surname"] = *u.Surname
	}
	if u.Country != nil {
		update["country"] = *u.Country
	}

	if len(update) == 0 {
		return nil
	}

	_, err = repo.collection.UpdateOne(
		ctx,
		bson.M{"_id": objID},
		bson.M{"$set": update},
	)
	if err != nil {
		return err
	}

	return nil
}

func (repo *UserService) MuteUnmuteUser(mute bool, id string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second) //si no lo encuentra error
	defer cancel()
	objID, err := primitive.ObjectIDFromHex(id)
	if err != nil {
		return err
	}

	var user User
	err = repo.collection.FindOne(ctx, bson.M{"_id": objID}).Decode(&user)
	if err != nil {
		return err
	}

	update := bson.M{"muteNotif": mute}
	_, err = repo.collection.UpdateOne(
		ctx,
		bson.M{"_id": objID},
		bson.M{"$set": update},
	)
	return err
}

func (repo *UserService) GetUsersByEmailPrefix(prefix string) ([]AppUser, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	
	filter := bson.M{
		"email": bson.M{
			"$regex":   "^" + prefix,
			"$options": "i",
		},
		"$or": bson.A{
			bson.M{"IsAdmin": bson.M{"$exists": false}},
			bson.M{"IsAdmin": false},
		},
	}
	
	opts := options.Find().SetLimit(10) //Limite
	
	cursor, err := repo.collection.Find(ctx, filter, opts)
	if err != nil {
		return nil, err
	}
	defer func() {
		if err := cursor.Close(ctx); err != nil {
			log.Println("Failed to close cursor:", err)
		}
	}()

	var users []AppUser
	for cursor.Next(ctx) {
		var u AppUser
		if err := cursor.Decode(&u); err != nil {
			log.Println("Failed to decode cursor result:", err)
		}
		users = append(users, u)
	}
	return users, nil
}

func buildUpdateData(u User) bson.M {
	/// Helper function. Returns bson for upsert with not null fields
	update := bson.M{}

	if u.UID != "" {
		update["uid"] = u.UID
	}
	if u.Token != "" {
		update["token"] = u.Token
	}
	if u.NotifToken != "" {
		update["notifToken"] = u.NotifToken
	}
	if u.Name != nil {
		update["name"] = *u.Name
	}
	if u.Surname != nil {
		update["surname"] = *u.Surname
	}
	if u.Email != "" {
		update["email"] = u.Email
	}
	if u.Country != nil {
		update["Country"] = u.Country
	}
	if u.IsAdmin {
		update["IsAdmin"] = true
	} else {
		update["IsAdmin"] = false
	}
	return update
}

func (repo *UserService) get_notif_tokens(users []string) []string {
    var objectIDs []primitive.ObjectID
    for _, idStr := range users {
		fmt.Println("Get notif for:",idStr)
		oid, err := primitive.ObjectIDFromHex(idStr)
        if err != nil {
            continue 
        }
		objectIDs = append(objectIDs, oid)
    }

    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
	
	filter := bson.M{
		"_id": bson.M{"$in": objectIDs}, 
		"$or": bson.A{
			bson.M{"muteNotif": bson.M{"$exists": false}},
			bson.M{"muteNotif": false},
		},
	}
    opts := options.Find().SetProjection(bson.M{"notifToken": 1})

    cursor, err := repo.collection.Find(ctx, filter, opts)
    if err != nil {
		var result []string
        return result
    }
	defer func() {
		if err := cursor.Close(ctx); err != nil {
			log.Printf("failed to close cursor: %v", err)
		}
	}()
	
    var tokens []string
    for cursor.Next(ctx) {
        var res struct {
            NotifToken string `bson:"notifToken"`
        }
        if err := cursor.Decode(&res); err == nil && res.NotifToken != "" {
            tokens = append(tokens, res.NotifToken)
        } else if err != nil {
			fmt.Println("Couldn't decode notif Token",err)
		} else {
			fmt.Println("notifToken is empty")
		}
    }

	fmt.Println("Tokens: ",tokens)
	
    return tokens
}

func (repo *UserService) get_name_and_emails(users []string) []NameEmail {
    var objectIDs []primitive.ObjectID
    for _, idStr := range users {
		fmt.Println("Get name and email for:",idStr)
		oid, err := primitive.ObjectIDFromHex(idStr)
        if err != nil {
            continue 
        }
		objectIDs = append(objectIDs, oid)
    }

    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
	
	filter := bson.M{
		"_id": bson.M{"$in": objectIDs}, 
		"$or": bson.A{
			bson.M{"muteNotif": bson.M{"$exists": false}},
			bson.M{"muteNotif": false},
		},
	}
    opts := options.Find().SetProjection(bson.M{"email": 1, "name": 1})

    cursor, err := repo.collection.Find(ctx, filter, opts)
    if err != nil {
		var result []NameEmail
        return result
    }
	defer func() {
		if err := cursor.Close(ctx); err != nil {
			log.Printf("failed to close cursor: %v", err)
		}
	}()
	
    var resultNameEmails []NameEmail
    for cursor.Next(ctx) {
        var res struct {
            Name string `bson:"name"`
            Email string `bson:"email"`
        }
        if err := cursor.Decode(&res); err == nil && res.Name != "" && res.Email != "" {
            resultNameEmails = append(resultNameEmails, NameEmail{name: res.Name, email: res.Email} )
        } else if err != nil {
			fmt.Println("Couldn't decode name or email",err)
		} else {
			fmt.Println("Name or email are empty")
		}
    }

	fmt.Println("Emails: ",resultNameEmails)
	
    return resultNameEmails
}

func (repo *UserService) SendNotification(notif Notification) error {
	firebase_result := repo.auth.SendNotification(notif.Title, notif.Message, notif.Metadata, repo.get_notif_tokens(notif.Users))
	brevo_result := repo.email.SendEmail(notif.TemplateId, notif.Title, notif.Message, repo.get_name_and_emails(notif.Users))

	if firebase_result != nil {
		return firebase_result
	} else if brevo_result != nil {
		return brevo_result
	} else {
		return nil
	}
}

/*
func (repo *UserService) format(user User) bson.M {
	return bson.M{
		"uid":     user.UID,
		"token":   user.Token,
		"name":    user.Name,
		"surname": user.Surname,
		"email":   user.Email,
		"Country": user.Country,
		"IsAdmin": user.IsAdmin,
	}
}
*/
