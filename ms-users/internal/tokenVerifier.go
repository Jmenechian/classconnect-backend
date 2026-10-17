package internal

import (
	"log"
	"context"
	"time"
	"errors"

	firebase "firebase.google.com/go/v4"
	"firebase.google.com/go/v4/messaging"
	"google.golang.org/api/option"
)

// Interfaz para abstraer la logica de verificacion de tokens 
// Permite desacoplar la aplicacion del servicio de autenticación utilizado, y facilitar el mockeo 
type tokenVerifier interface {
	VerifyToken(token string) (bool, error)
	SendNotification(title string, message string, metadata map[string]string, tokens []string ) error
}

type tokenService struct {
	auth			*firebase.App
	messageClient	*messaging.Client
}

func NewTokenService() tokenVerifier {
    ctx := context.Background()

    app, err := firebase.NewApp(ctx, &firebase.Config{
        ProjectID: "classconnect13",
    }, option.WithCredentialsFile("authKey.json")) 
    if err != nil {
        log.Fatalf("error initializing Firebase App: %v", err)
        return nil
    }

    client, err := app.Messaging(ctx)
    if err != nil {
        log.Fatalf("error creating Messaging client: %v", err)
        return nil
    }

    return &tokenService{
        auth:          app,
        messageClient: client,
    }
/*
	app, err := firebase.NewApp(context.Background(), nil)
	if err != nil {
		log.Fatalf("error initializing auth app: %v\n", err)
		return nil
	}
	client, err := app.Messaging(context.Background())
	if err != nil {
		return nil
	}
	return &tokenService{auth: app, messageClient: client}
*/
}

func (repo *tokenService) VerifyToken(token string) (bool, error) {
	log.Printf("Received token: %s", token)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	client, err := repo.auth.Auth(ctx)
	if err != nil {
		return false, errors.New("500 Internal server error: Firebase problem")
	}

	_, err = client.VerifyIDToken(ctx, token)

	return err == nil, err
}

func (repo *tokenService) SendNotification(title string, message string, metadata map[string]string, tokens []string) error {
	ctx := context.Background()

	if metadata == nil {
		metadata = make(map[string]string)
	}

	metadata["message"] = message

	for _, token := range tokens {
		msg := &messaging.Message{
			Notification: &messaging.Notification{
				Title: title,
				Body:  message,
			},
			Data: metadata,
			Token: token,
		}

		resp, err := repo.messageClient.Send(ctx, msg)
		if err != nil {
			log.Printf("Error sending to token %s: %v", token, err)
			continue 
		}
		log.Printf("Successfully sent to token %s: %s", token, resp)
	}

	return nil	
	/*
	notif_message := &messaging.MulticastMessage{
    	Data:map[string]string{"message": message},
    	Tokens: tokens,
	}
	resp, err := repo.messageClient.SendMulticast(context.Background(), notif_message)
	if err != nil {
    		log.Printf("SendMulticast error: %v", err)
	} else {
		log.Printf("Successfully sent %d messages", resp.SuccessCount)
	}
	return err
	*/
}
