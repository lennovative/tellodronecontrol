from djitellopy import Tello

drone = Tello()

drone.connect()

drone.takeoff()
drone.land()

drone.end()
