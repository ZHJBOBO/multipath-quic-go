package congestion

import (
	"time"

	"github.com/ZHJBOBO/multipath-quic-go/internal/protocol"
)

// A SendAlgorithm performs congestion control and calculates the congestion window
type SendAlgorithm interface {
	TimeUntilSend(now time.Time, bytesInFlight protocol.ByteCount) time.Duration
	OnPacketSent(sentTime time.Time, bytesInFlight protocol.ByteCount, packetNumber protocol.PacketNumber, bytes protocol.ByteCount, isRetransmittable bool) bool
	GetCongestionWindow() protocol.ByteCount
	MaybeExitSlowStart()
	OnPacketAcked(number protocol.PacketNumber, ackedBytes protocol.ByteCount, bytesInFlight protocol.ByteCount)
	OnPacketLost(number protocol.PacketNumber, lostBytes protocol.ByteCount, bytesInFlight protocol.ByteCount)
	SetNumEmulatedConnections(n int)
	OnRetransmissionTimeout(packetsRetransmitted bool)
	OnConnectionMigration()
	RetransmissionDelay() time.Duration
	SmoothedRTT() time.Duration
	//SBD
	UpdateGroupEpoch(group uint8, epoch uint16)

	// Experiments
	SetSlowStartLargeReduction(enabled bool)
}

// SendAlgorithmWithDebugInfo adds some debug functions to SendAlgorithm
type SendAlgorithmWithDebugInfo interface {
	SendAlgorithm
	BandwidthEstimate() Bandwidth

	// Stuff only used in testing

	HybridSlowStart() *HybridSlowStart
	SlowstartThreshold() protocol.PacketNumber
	RenoBeta() float32
	InRecovery() bool
}
