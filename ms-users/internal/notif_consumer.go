package internal

import (
	"encoding/json"
	"log"
	"os"
	"time"

	"github.com/streadway/amqp"
)

func ConsumeNotifications(app *App) {
	log.Printf("Notifications Consumer: start consuming notifications with RabbitMQ")
	for {
		err := startConsumer(app)
		if err != nil {
			log.Printf("Consumer error: %s. Retrying in 5 seconds...", err)
			time.Sleep(5 * time.Second)
			continue
		}
		// If startConsumer returns without error, it means that the connection was closed and we should reconnect
		log.Println("Notifications Consumer: connection closed, reconnecting...")
	}
}

func startConsumer(app *App) error {
	conn, err := amqp.Dial(os.Getenv("CLOUDAMQP_URL"))
	if err != nil {
		return err
	}
	defer func() {
		if err := conn.Close(); err != nil {
			log.Printf("Notifications Consumer: failed to close AMQP connection: %v", err)
		}
	}()

	ch, err := conn.Channel()
	if err != nil {
		return err
	}
	defer func() {
		if err := ch.Close(); err != nil {
			log.Printf("Notifications Consumer: failed to close AMQP channel: %v", err)
		}
	}()

	// Config to detect channel closing
	notifyClose := make(chan *amqp.Error)
	ch.NotifyClose(notifyClose)

	args := amqp.Table{"x-message-ttl": int32(86400000)}
	q, err := ch.QueueDeclare("notifications", true, false, false, false, args)
	if err != nil {
		return err
	}

	msgs, err := ch.Consume(q.Name, "", false, false, false, false, nil)
	if err != nil {
		return err
	}

	// Goroutine to handle unexpected channel close
	done := make(chan bool)
	go func() {
		err := <-notifyClose
		if err != nil {
			log.Printf("Notifications Consumer: consumer channel closed unexpectedly: %v", err)
			done <- true
		}
	}()

	for {
		select {
		case d, ok := <-msgs:
			if !ok {
				// Channel closed, exit to reconnect
				return nil
			}

			var notif Notification
			if err := json.Unmarshal(d.Body, &notif); err != nil {
				log.Println("Notifications Consumer: failed to parse message:", err)
				if err := d.Nack(false, false); err != nil {
					log.Printf("Notifications Consumer: failed to Nack message: %v", err)
				}
				continue
			}

			log.Printf("Notifications Consumer: processing notification: %+v\n", notif)

			if err := app.Repository.SendNotification(notif); err != nil {
				log.Println("Notifications Consumer: notification failed, requeuing:", err)
				if err := d.Nack(false, true); err != nil { // Reinsert to queue to retry
					log.Printf("Notifications Consumer: failed to Nack message: %v", err)
				}
				continue
			}

			if err := d.Ack(false); err != nil { // Successful processing
				log.Printf("Notifications Consumer: failed to Ack message: %v", err)
			} else {
				log.Printf("Notifications Consumer: notification successfully processed: %+v", notif)
			}

		case <-done:
			// Received unexpected close signal
			return nil
		}
	}
}