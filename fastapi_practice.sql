-- phpMyAdmin SQL Dump
-- version 5.1.3
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Aug 03, 2026 at 06:35 PM
-- Server version: 10.4.22-MariaDB
-- PHP Version: 7.4.29

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `fastapi_practice`
--

-- --------------------------------------------------------

--
-- Table structure for table `dcr_reports`
--

CREATE TABLE `dcr_reports` (
  `id` bigint(20) NOT NULL,
  `file_name` varchar(255) DEFAULT NULL,
  `report_date` bigint(20) NOT NULL DEFAULT 0,
  `cinema_name` varchar(255) DEFAULT NULL,
  `distributor_address` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `report_data` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- --------------------------------------------------------

--
-- Table structure for table `dcr_report_details`
--

CREATE TABLE `dcr_report_details` (
  `id` bigint(20) NOT NULL,
  `report_id` bigint(20) NOT NULL DEFAULT 0,
  `day` varchar(255) DEFAULT NULL,
  `shows` bigint(20) NOT NULL DEFAULT 0,
  `audience` bigint(20) NOT NULL DEFAULT 0,
  `final_net` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `dcr_reports`
--
ALTER TABLE `dcr_reports`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `dcr_report_details`
--
ALTER TABLE `dcr_report_details`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `dcr_reports`
--
ALTER TABLE `dcr_reports`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `dcr_report_details`
--
ALTER TABLE `dcr_report_details`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
