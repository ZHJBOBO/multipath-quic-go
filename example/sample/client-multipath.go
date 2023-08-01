package main

import (
	"crypto/tls"
	"fmt"
	quic "github.com/ZHJBOBO/multipath-quic-go"
	"github.com/ZHJBOBO/multipath-quic-go/example/sample/config"
	"github.com/ZHJBOBO/multipath-quic-go/example/sample/utils"
	"os"
	"strconv"
	"time"
)

const threshold = 5 * 1024 // 1KB

func main() {

	//mp_flag, err := strconv.ParseBool(os.Args[1])
	mp_flag, err := strconv.ParseBool("true")

	quicConfig := &quic.Config{
		CreatePaths: mp_flag,
	}

	//addr := os.Args[2] + ":" + config.PORT
	addr := "127.0.0.1:" + config.PORT

	//addr := "10.203.231.253:4242"
	//fileToSend := os.Args[3]
	fileToSend := "D:\\all_corpus\\mozilla"
	fmt.Println("Server Address: ", addr)
	fmt.Println("Sending File: ", fileToSend)

	file, err := os.Open(fileToSend)
	utils.HandleError(err)

	if quicConfig.CreatePaths == false {
		fmt.Println("use single path.")
	} else {
		fmt.Println("use multipath.")
	}
	file.Close()

	fmt.Println("Trying to connect to: ", addr)
	sess, err := quic.DialAddr(addr, &tls.Config{InsecureSkipVerify: true}, quicConfig)
	utils.HandleError(err)

	fmt.Println("session created: ", sess.RemoteAddr())

	stream, err := sess.OpenStream()
	utils.HandleError(err)

	fmt.Println("stream created...")
	fmt.Println("Client connected")
	sendFile(stream, fileToSend)
	time.Sleep(2 * time.Second)

}

func sendFile(stream quic.Stream, fileToSend string) {
	fmt.Println("A client has connected!")
	defer stream.Close()

	file, err := os.Open(fileToSend)
	utils.HandleError(err)

	fileInfo, err := file.Stat()
	utils.HandleError(err)

	fileSize := utils.FillString(strconv.FormatInt(fileInfo.Size(), 10), 10)
	fileName := utils.FillString(fileInfo.Name(), 64)

	fmt.Println("Sending filename and filesize!")
	stream.Write([]byte(fileSize))
	stream.Write([]byte(fileName))

	sendBuffer := make([]byte, config.BUFFERSIZE)
	fmt.Println("Start sending file!\n")

	var sentBytes int64
	start := time.Now()

	for {
		sentSize, err := file.Read(sendBuffer)
		if err != nil {
			break
		}

		stream.Write(sendBuffer)
		if err != nil {
			break
		}

		sentBytes += int64(sentSize)
		fmt.Printf("\033[2K\rSent: %d / %d", sentBytes, fileInfo.Size())
	}
	elapsed := time.Since(start)
	fmt.Println("\nTransfer took: ", elapsed)

	stream.Close()
	stream.Close()
	time.Sleep(2 * time.Second)
	fmt.Println("\n\nFile has been sent, closing stream!")
	return
}
