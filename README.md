# FLL/FTC/FRC Event Attendance Registrar
### https://roboregistry.vercel.app/
##### Automated Registry for Recording and Tracking FIRST Scrimmage Attendance
[![CodeFactor](https://www.codefactor.io/repository/github/hololb/roboregistry/badge)](https://www.codefactor.io/repository/github/hololb/roboregistry)
___

RoboRegistry is a digital registrar designed to hold information regarding schools and teams participating in a FIRST scrimmage event. The primary goal of this application is to avoid the need for manual data collection by exporting and using data to determine event statistics, all from one centralised place.

![RoboRegistry](https://i.imgur.com/8mau56s.png)

The register can be used to compile data for planning, reporting, and/or inclusion in funding grant proposals. For instance, prior to the event, teams are required to register for attendance and provide information such as their FIRST Team Number (if registered), estimated number of people attending, and nominated point of contact for teams (email and mobile).

During a specified event, the application utilises a QR code check-in process with online sign-up and prerequisite beforehand. As teams prerequisitely register, their team number will be fetched with the [FIRSTTeamAPI](https://github.com/hololb/FIRSTTeamAPI), simplifying the registering process in a simple, modern, and accessible web UI. Once the event is over, the data can be exported or viewed at the event owner's discretion.

###### Copyright (c) 2023 Lucas Bubner under the [BSD 3-Clause Clear License](https://raw.githubusercontent.com/hololb/RoboRegistry/prod/LICENSE).
